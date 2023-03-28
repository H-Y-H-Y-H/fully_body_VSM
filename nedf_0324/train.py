import os
import random
import torch
from model import NeDF
from tqdm import trange
import numpy as np
import matplotlib.image

from func import *

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(device)

"""training process"""

def train(model, optimizer, n_iter):

    train_psnrs = []

    for i in trange(n_iter):
        model.train()
        if Overfitting_test:
            target_img_idx = 0
        else:
            target_img_idx = np.random.randint(training_img.shape[0] - 1)

        target_img = training_img[target_img_idx]
        # angle = training_angles[target_img_idx]
        pose_matrix = training_pose_matrix[target_img_idx]

        rays_o, rays_d = get_rays(height, width, focal, pose_matrix)

        rays_o = rays_o.reshape([-1, 3])  # ?
        rays_d = rays_d.reshape([-1, 3])
        target_img = target_img.reshape([-1])

        outputs = NeDF_forward(
            rays_o, rays_d, near, far, model, chunk_size, n_samples
        )

        # Backprop!
        rgb_predicted = outputs['rgb_map']
        loss = nn.MSELoss(rgb_predicted, target_img)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        # Compute mean-squared error between predicted and target images.
        psnr = -10. * torch.log10(loss)
        train_psnrs.append(psnr.item())

        if i % display_rate == 0:
            model.eval()

            # todo check the code below:
            # valid_epoch_loss = []
            # valid_psnr = []
            # valid_image = []
            # # height, width = testing_img[0].shape[:2]
            #
            # if Overfitting_test:
            #     target_img_idx = 0
            #     target_img = training_img[target_img_idx]
            #     angle = training_angles[target_img_idx]
            #
            #     rays_o, rays_d = get_fixed_camera_rays(height, width, focal, distance2camera=4)
            #     rays_o = rays_o.reshape([-1, 3])
            #     rays_d = rays_d.reshape([-1, 3])
            #     outputs = nerf_forward(rays_o, rays_d,
            #                            near, far, model,
            #                            kwargs_sample_stratified=kwargs_sample_stratified,
            #                            n_samples_hierarchical=n_samples_hierarchical,
            #                            kwargs_sample_hierarchical=kwargs_sample_hierarchical,
            #                            chunksize=chunksize,
            #                            arm_angle=angle,
            #                            DOF=DOF)
            #
            #     rgb_predicted = outputs['rgb_map']
            #
            #     loss = torch.nn.functional.mse_loss(rgb_predicted, target_img.reshape(-1))
            #     val_psnr = (-10. * torch.log10(loss)).item()
            #     valid_epoch_loss = loss.item()
            #     np_image = rgb_predicted.reshape([height, width, 1]).detach().cpu().numpy()
            #     np_image = np.clip(0, 1, np_image)
            #     np_image_combine = np.dstack((np_image, np_image, np_image))
            #     matplotlib.image.imsave(LOG_PATH + 'image/' + 'overfitting%d.png' % i, np_image_combine)
            #
            #     psnr_v = val_psnr
            #     val_psnrs.append(psnr_v)
            #     print("Loss:", valid_epoch_loss, "PSNR: ", psnr_v)
            #
            # else:
            #     for v_i in range(valid_amount):
            #         angle = testing_angles[v_i]
            #         img_label = testing_img[v_i]
            #         pose_matrix = testing_pose_matrix[v_i]
            #
            #         rays_o, rays_d = get_rays(height, width, focal, c2w=pose_matrix)
            #         # rays_o, rays_d = get_fixed_camera_rays(height, width, focal, distance2camera=4)
            #         rays_o = rays_o.reshape([-1, 3])
            #         rays_d = rays_d.reshape([-1, 3])
            #         outputs = nerf_forward(rays_o, rays_d,
            #                                near, far, model,
            #                                kwargs_sample_stratified=kwargs_sample_stratified,
            #                                n_samples_hierarchical=n_samples_hierarchical,
            #                                kwargs_sample_hierarchical=kwargs_sample_hierarchical,
            #                                chunksize=chunksize,
            #                                arm_angle=angle,
            #                                DOF=DOF)
            #
            #         rgb_predicted = outputs['rgb_map']
            #         # img_label = torch.dstack((testing_img[v_i],testing_img[v_i],testing_img[v_i]))
            #
            #         loss = torch.nn.functional.mse_loss(rgb_predicted, img_label.reshape(-1))
            #         val_psnr = (-10. * torch.log10(loss)).item()
            #         valid_epoch_loss.append(loss.item())
            #         valid_psnr.append(val_psnr)
            #         np_image = rgb_predicted.reshape([height, width, 1]).detach().cpu().numpy()
            #         np_image = np.clip(0, 1, np_image)
            #         if v_i < max_pic_save:
            #             valid_image.append(np_image)
            #     psnr_v = np.mean(valid_psnr)
            #     val_psnrs.append(psnr_v)
            #     print("Loss:", np.mean(valid_epoch_loss), "PSNR: ", psnr_v)
            #
            #     # save test image
            #     np_image_combine = np.hstack(valid_image)
            #     np_image_combine = np.dstack((np_image_combine, np_image_combine, np_image_combine))
            #
            #     matplotlib.image.imsave(LOG_PATH + 'image/' + 'latest.png', np_image_combine)
            #     if Flag_save_image_during_training:
            #         matplotlib.image.imsave(LOG_PATH + 'image/' + '%d.png' % i, np_image_combine)
            #
            #     record_file_train.write(str(psnr) + "\n")
            #     record_file_val.write(str(psnr_v) + "\n")
            #
            #     if psnr_v > best_psnr:
            #         """record the best image and model"""
            #         best_psnr = psnr_v
            #         matplotlib.image.imsave(LOG_PATH + 'image/' + 'best.png', np_image_combine)
            #         torch.save(model.state_dict(), LOG_PATH + 'best_model/nerf.pt')
            #         patience = 0
            #     else:
            #         patience += 1
            #     os.makedirs(LOG_PATH + "epoch_%d_model" % i, exist_ok=True)
            #     torch.save(model.state_dict(), LOG_PATH + 'epoch_%d_model/nerf.pt' % i)

    pass


if __name__ == "__main__":

    seed_num = 6
    np.random.seed(seed_num)
    random.seed(seed_num)
    torch.manual_seed(seed_num)

    """
    prepare data and parameters
    """
    near, far = 2., 6.
    Flag_save_image_during_training = True
    DOF = 3  # the number of motors
    num_data = 40
    tr = 0.8  # training ratio
    data = np.load('../data/NeDF_data/dof%d_data%d.npz' % (DOF, num_data))
    Overfitting_test = False
    sample_id = random.sample(range(num_data), num_data)

    chunk_size = 2 ** 14  # Modify as needed to fit in GPU memory
    n_samples = 64  # Number of spatial samples per ray
    display_rate = 20  # Display test output every X epochs

    if Overfitting_test:
        valid_img_visual = data['images'][sample_id[0]]
        valid_img_visual = np.dstack((valid_img_visual, valid_img_visual, valid_img_visual))
    else:
        valid_amount = int(num_data * (1 - tr))
        max_pic_save = 8
        valid_img_visual = []
        for vimg in range(max_pic_save):
            valid_img_visual.append(data['images'][sample_id[int(num_data * tr) + vimg]])
        valid_img_visual = np.hstack(valid_img_visual)
        valid_img_visual = np.dstack((valid_img_visual, valid_img_visual, valid_img_visual))

    # Gather as torch tensors
    focal = torch.from_numpy(data['focal'].astype('float32')).to(device)

    training_img = torch.from_numpy(data['images'][sample_id[:int(num_data * tr)]].astype('float32')).to(device)
    training_angles = torch.from_numpy(data['angles'][sample_id[:int(num_data * tr)]].astype('float32')).to(device)
    training_pose_matrix = torch.from_numpy(data['poses'][sample_id[:int(num_data * tr)]].astype('float32')).to(device)

    testing_img = torch.from_numpy(data['images'][sample_id[int(num_data * tr):]].astype('float32')).to(device)
    testing_angles = torch.from_numpy(data['angles'][sample_id[int(num_data * tr):]].astype('float32')).to(device)
    testing_pose_matrix = torch.from_numpy(data['poses'][sample_id[int(num_data * tr):]].astype('float32')).to(device)

    # Grab rays from sample image
    height, width = training_img.shape[1:3]
    print('IMG (height, width)', (height, width))

    """
    init model
    """
    Model = NeDF(d_input=3,
                 n_layers=6,
                 d_filter=256)
    Model.to(device)

    Learning_rate = 5e-5
    Optimizer = torch.optim.Adam(Model.parameters(), lr=Learning_rate)

    """
    training
    """

    # Run training session(s)
    LOG_PATH = "train_log/log_%ddata/" % num_data

    os.makedirs(LOG_PATH + "image/", exist_ok=True)
    os.makedirs(LOG_PATH + "best_model/", exist_ok=True)

    record_file_train = open(LOG_PATH + "log_train.txt", "w")
    record_file_val = open(LOG_PATH + "log_val.txt", "w")
    Patience_threshold = 20

    # Save testing gt image for visualization
    matplotlib.image.imsave(LOG_PATH + 'image/' + 'gt.png', valid_img_visual)

    # train(model=Model,
    #       optimizer=Optimizer,
    #       n_iter=10000)