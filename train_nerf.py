#  from notebook: https://towardsdatascience.com/its-nerf-from-nothing-build-a-vanilla-nerf-with-pytorch-7846e4c45666
from model import FBV_SM, PositionalEncoder
from func import *

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(device)

"""
prepare data and parameters
"""

near, far = 2., 6.
n_training = 100
testimg_idx = 101
DOF = 2  # the number of motors
num_data = 110
data = np.load('data/arm_data/dof%d_data%d.npz' % (DOF, num_data))
# data = np.load('NeRF_pytorch/tiny_nerf_data.npz') #FBV_SM original Demo

# Gather as torch tensors
images = torch.from_numpy(data['images'].astype('float32')[:n_training]).to(device)
poses = torch.from_numpy(data['poses'].astype('float32')).to(device)
focal = torch.from_numpy(data['focal'].astype('float32')).to(device)

testimg = torch.from_numpy(data['images'].astype('float32')[testimg_idx]).to(device)
testpose = torch.from_numpy(data['poses'].astype('float32')[testimg_idx]).to(device)

# Grab rays from sample image
height, width = images.shape[1:3]
print('IMG (height, width)', (height, width))

# Encoders
"""arm dof=2, input=3;  arm dof=3, input=4"""
d_input = 3  # Number of input dimensions
if d_input == 4:
    angles = torch.from_numpy(data['angles'].astype('float32')).to(device)
    testangle = torch.tensor(data['angles'][testimg_idx].astype('float32')).to(device)
else:
    angles = torch.tensor([])
    testangle = torch.tensor([])

n_freqs = 10  # Number of encoding functions for samples
log_space = True  # If set, frequencies scale in log space
use_viewdirs = False  # If set, use view direction as input  # check here
n_freqs_views = 4  # Number of encoding functions for views

# Stratified sampling
n_samples = 64  # Number of spatial samples per ray
perturb = True  # If set, applies noise to sample positions
inverse_depth = False  # If set, samples points linearly in inverse depth

# Model
d_filter = 128  # Dimensions of linear layer filters
n_layers = 2  # Number of layers in network bottleneck
skip = []  # Layers at which to apply input residual
use_fine_model = True  # If set, creates a fine model
d_filter_fine = 128  # Dimensions of linear layer filters of fine network
n_layers_fine = 6  # Number of layers in fine network bottleneck

# Hierarchical sampling
n_samples_hierarchical = 64  # Number of samples per ray
perturb_hierarchical = False  # If set, applies noise to sample positions

# Optimizer
lr = 5e-4  # Learning rate

# Training
n_iters = 10000
batch_size = 2 ** 14  # Number of rays per gradient step (power of 2)
one_image_per_step = True  # One image per gradient step (disables batching)
chunksize = 2 ** 14  # Modify as needed to fit in GPU memory
center_crop = True  # Crop the center of image (one_image_per_)
center_crop_iters = 50  # Stop cropping center after this many epochs
display_rate = 25  # Display test output every X epochs

# Early Stopping
warmup_iters = 100  # Number of iterations during warmup phase
warmup_min_fitness = 10.0  # Min val PSNR to continue training at warmup_iters
n_restarts = 10  # Number of times to restart if training stalls

# We bundle the kwargs for various functions to pass all at once.
kwargs_sample_stratified = {
    'n_samples': n_samples,
    'perturb': perturb,
    'inverse_depth': inverse_depth
}
kwargs_sample_hierarchical = {
    'perturb': perturb
}


def plot_samples(
        z_vals: torch.Tensor,
        z_hierarch: Optional[torch.Tensor] = None,
        ax: Optional[np.ndarray] = None):
    r"""
  Plot stratified and (optional) hierarchical samples.
  """
    y_vals = 1 + np.zeros_like(z_vals)

    if ax is None:
        ax = plt.subplot()
    ax.plot(z_vals, y_vals, 'b-o')
    if z_hierarch is not None:
        y_hierarch = np.zeros_like(z_hierarch)
        ax.plot(z_hierarch, y_hierarch, 'r-o')
    ax.set_ylim([-1, 2])
    ax.set_title('Stratified  Samples (blue) and Hierarchical Samples (red)')
    ax.axes.yaxis.set_visible(False)
    ax.grid(True)
    return ax


def crop_center(
        img: torch.Tensor,
        frac: float = 0.5
) -> torch.Tensor:
    r"""
  Crop center square from image.
  """
    h_offset = round(img.shape[0] * (frac / 2))
    w_offset = round(img.shape[1] * (frac / 2))
    return img[h_offset:-h_offset, w_offset:-w_offset]


class EarlyStopping:
    r"""
  Early stopping helper based on fitness criterion.
  """

    def __init__(
            self,
            patience: int = 30,
            margin: float = 1e-4
    ):
        self.best_fitness = 0.0  # In our case PSNR
        self.best_iter = 0
        self.margin = margin
        self.patience = patience or float('inf')  # epochs to wait after fitness stops improving to stop

    def __call__(
            self,
            iter: int,
            fitness: float
    ):
        r"""
    Check if criterion for stopping is met.
    """
        if (fitness - self.best_fitness) > self.margin:
            self.best_iter = iter
            self.best_fitness = fitness
        delta = iter - self.best_iter
        stop = delta >= self.patience  # stop training if patience exceeded
        return stop


def init_models():
    r"""
  Initialize models, encoders, and optimizer for NeRF training.
  """
    # Encoders
    encoder = PositionalEncoder(d_input, n_freqs, log_space=log_space)
    encode = lambda x: encoder(x)

    # View direction encoders
    if use_viewdirs:
        encoder_viewdirs = PositionalEncoder(d_input, n_freqs_views,
                                             log_space=log_space)
        encode_viewdirs = lambda x: encoder_viewdirs(x)
        d_viewdirs = encoder_viewdirs.d_output
    else:
        encode_viewdirs = None
        d_viewdirs = None

    # Models
    model = FBV_SM(encoder.d_output, n_layers=n_layers, d_filter=d_filter, skip=skip,
                 d_viewdirs=d_viewdirs)
    model.to(device)
    model_params = list(model.parameters())
    if use_fine_model:
        fine_model = FBV_SM(encoder.d_output, n_layers=n_layers, d_filter=d_filter, skip=skip,
                          d_viewdirs=d_viewdirs)
        fine_model.to(device)
        model_params = model_params + list(fine_model.parameters())
    else:
        fine_model = None

    # Optimizer
    optimizer = torch.optim.Adam(model_params, lr=lr)

    # Early Stopping
    warmup_stopper = EarlyStopping(patience=50)

    return model, fine_model, encode, encode_viewdirs, optimizer, warmup_stopper


def train(model, fine_model, encode, encode_viewdirs, optimizer, warmup_stopper):
    r"""
    Launch training session for NeRF.
    """
    # Shuffle rays across all images.
    if not one_image_per_step:
        height, width = images.shape[1:3]

        # get_rays -> (rays_o, rays_d): ray origins and ray directions.

        all_rays = torch.stack([torch.stack(get_rays(height, width, focal, p), 0) for p in poses[:n_training]], 0)
        rays_rgb = torch.cat([all_rays, images[:, None]], 1)
        rays_rgb = torch.permute(rays_rgb, [0, 2, 3, 1, 4])
        rays_rgb = rays_rgb.reshape([-1, 3, 3])
        rays_rgb = rays_rgb.type(torch.float32)
        rays_rgb = rays_rgb[torch.randperm(rays_rgb.shape[0])]
        i_batch = 0

    train_psnrs = []
    val_psnrs = []
    iternums = []
    best_psnr = 0.
    for i in trange(n_iters):
        patience = 0
        model.train()

        if one_image_per_step:
            # Randomly pick an image as the target.
            target_img_idx = np.random.randint(images.shape[0])
            target_img = images[target_img_idx].to(device)
            """one more dof"""
            if d_input == 4:
                angle = angles[target_img_idx].to(device)
            else:
                angle = 1.

            if center_crop and i < center_crop_iters:
                target_img = crop_center(target_img)
            height, width = target_img.shape[:2]
            target_pose = poses[target_img_idx].to(device)
            rays_o, rays_d = get_rays(height, width, focal, target_pose)
            rays_o = rays_o.reshape([-1, 3])
            rays_d = rays_d.reshape([-1, 3])
        else:
            # Random over all images.
            batch = rays_rgb[i_batch:i_batch + batch_size]
            batch = torch.transpose(batch, 0, 1)
            rays_o, rays_d, target_img = batch
            height, width = target_img.shape[:2]
            i_batch += batch_size
            # Shuffle after one epoch
            if i_batch >= rays_rgb.shape[0]:
                rays_rgb = rays_rgb[torch.randperm(rays_rgb.shape[0])]
                i_batch = 0
        target_img = target_img.reshape([-1, 3])

        # Run one iteration of TinyNeRF and get the rendered RGB image.
        outputs = nerf_forward(rays_o, rays_d,
                               near, far, encode, model,
                               kwargs_sample_stratified=kwargs_sample_stratified,
                               n_samples_hierarchical=n_samples_hierarchical,
                               kwargs_sample_hierarchical=kwargs_sample_hierarchical,
                               fine_model=fine_model,
                               viewdirs_encoding_fn=encode_viewdirs,
                               chunksize=chunksize,
                               arm_angle=angle,
                               if_3dof=(d_input == 4))

        # Check for any numerical issues.
        for k, v in outputs.items():
            if torch.isnan(v).any():
                print(f"! [Numerical Alert] {k} contains NaN.")
            if torch.isinf(v).any():
                print(f"! [Numerical Alert] {k} contains Inf.")

        # Backprop!
        rgb_predicted = outputs['rgb_map']
        loss = torch.nn.functional.mse_loss(rgb_predicted, target_img)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        # Compute mean-squared error between predicted and target images.
        psnr = -10. * torch.log10(loss)
        train_psnrs.append(psnr.item())

        # Evaluate testimg at given display rate.
        if i % display_rate == 0:
            model.eval()
            height, width = testimg.shape[:2]
            rays_o, rays_d = get_rays(height, width, focal, testpose)
            rays_o = rays_o.reshape([-1, 3])
            rays_d = rays_d.reshape([-1, 3])
            outputs = nerf_forward(rays_o, rays_d,
                                   near, far, encode, model,
                                   kwargs_sample_stratified=kwargs_sample_stratified,
                                   n_samples_hierarchical=n_samples_hierarchical,
                                   kwargs_sample_hierarchical=kwargs_sample_hierarchical,
                                   fine_model=fine_model,
                                   viewdirs_encoding_fn=encode_viewdirs,
                                   chunksize=chunksize,
                                   arm_angle=testangle,
                                   if_3dof=(d_input == 4))

            rgb_predicted = outputs['rgb_map']
            loss = torch.nn.functional.mse_loss(rgb_predicted, testimg.reshape(-1, 3))
            print("Loss:", loss.item(), "PSNR: ", psnr)
            val_psnr = -10. * torch.log10(loss)

            val_psnrs.append(val_psnr.item())
            iternums.append(i)
            # save test image
            np_image = rgb_predicted.reshape([height, width, 3]).detach().cpu().numpy()
            matplotlib.image.imsave(LOG_PATH + 'image/' + 'latest.png', np_image)
            matplotlib.image.imsave(LOG_PATH + 'image/' + '%d.png' % i, np_image)

            record_file_train.write(str(psnr.cpu().detach().numpy()) + "\n")
            record_file_val.write(str(val_psnr.cpu().detach().numpy()) + "\n")

            if val_psnr > best_psnr:
                """record the best image and model"""
                best_psnr = val_psnr
                matplotlib.image.imsave(LOG_PATH + 'image/' + 'best.png', np_image)
                torch.save(model.state_dict(), LOG_PATH + 'best_model/nerf.pt')
                torch.save(fine_model.state_dict(), LOG_PATH + 'best_model/nerf-fine.pt')

                patience = 0

            else:
                patience += 1

        # Check PSNR for issues and stop if any are found.
        if i == warmup_iters - 1:
            if val_psnr < warmup_min_fitness:
                print(f'Val PSNR {val_psnr} below warmup_min_fitness {warmup_min_fitness}. Stopping...')
                return False, train_psnrs, val_psnrs
        elif i < warmup_iters:
            if warmup_stopper is not None and warmup_stopper(i, psnr):
                print(f'Train PSNR flatlined at {psnr} for {warmup_stopper.patience} iters. Stopping...')
                return False, train_psnrs, val_psnrs

        if patience > Patience_threshold:
            break

    return True, train_psnrs, val_psnrs


if __name__ == "__main__":
    # Run training session(s)
    LOG_PATH = "train_log/log_debug/"

    os.makedirs(LOG_PATH + "image/", exist_ok=True)
    os.makedirs(LOG_PATH + "best_model/", exist_ok=True)

    record_file_train = open(LOG_PATH + "log_loss_train.txt", "w")
    record_file_val = open(LOG_PATH + "log_loss_val.txt", "w")
    Patience_threshold = 100

    for _ in range(n_restarts):
        model, fine_model, encode, encode_viewdirs, optimizer, warmup_stopper = init_models()
        success, train_psnrs, val_psnrs = train(model, fine_model, encode, encode_viewdirs, optimizer, warmup_stopper)
        if success and val_psnrs[-1] >= warmup_min_fitness:
            print('Training successful!')
            break

    print('')
    print(f'Done!')
    record_file_train.close()
    record_file_val.close()

    # torch.save(model.state_dict(), LOG_PATH + 'nerf.pt')
    # torch.save(fine_model.state_dict(), LOG_PATH + 'nerf-fine.pt')