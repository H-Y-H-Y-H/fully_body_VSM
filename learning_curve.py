import numpy as np
import matplotlib.pyplot as plt


class LearningCurve:
    def __init__(self, dists, start, epoch):
        self.dists = dists
        self.seeds = [0, 1, 3]
        self.start = start
        self.epoch = epoch
        self.curve_dict = {}
        for dist in dists:
            # self.load_data(dist)
            self.load_data(dist, sep=True)


    def load_data(self, dist, sep=False):
        curve = []
        for seed in self.seeds:
            if sep:
                path = "train_log_model/%s_id%d_%d(%d)_%s(%s)_cam%d(%d)_sep" % ('sim', 0, 8000, seed, 'PE', 'arm', dist * 1000, seed)
            else:
                path = "train_log_model/%s_id%d_%d(%d)_%s(%s)_cam%d(%d)" % ('sim', 0, 8000, seed, 'PE', 'arm', dist * 1000, seed)
            # train_log = np.loadtxt(path + "/log_train.txt")[-self.epoch:] # shape: (epoch,)
            # val_log = np.loadtxt(path + "/log_val.txt")[-self.epoch:] # shape: (epoch,)
            train_log = np.loadtxt(path + "/log_train.txt")[self.start:self.epoch] # shape: (epoch,)
            val_log = np.loadtxt(path + "/log_val.txt")[self.start:self.epoch] # shape: (epoch,)
            log = np.vstack((train_log, val_log)) # shape: (2, epoch)

            curve.append(log)

        curve = np.array(curve) # shape: (3, 2, epoch)
        print(curve.shape)
        # if sep:
        #     self.curve_dict[dist+1] = curve
        # else:
        #     self.curve_dict[dist] = curve # dictionary: {dist: (3, 2, epoch)}

        self.curve_dict[dist] = curve

            

    def plot_curves(self):
        plt.figure(figsize=(8, 5))
        # plt.style.use('seaborn')
        x = np.arange(self.start, self.epoch)
        for dist in self.dists:
            y = np.mean(self.curve_dict[dist][:, 1], axis=0) * (dist * dist) # shape: (epoch,)
            yerr = np.std(self.curve_dict[dist][:, 1], axis=0) * (dist * dist) # shape: (epoch,)

            # y_sep = np.mean(self.curve_dict[dist+1][:, 1], axis=0) * (dist * dist) # shape: (epoch,)
            # yerr_sep = np.std(self.curve_dict[dist+1][:, 1], axis=0) * (dist * dist) # shape: (epoch,)
            
            y_t = np.mean(self.curve_dict[dist][:, 0], axis=0) * (dist * dist) # shape: (epoch,)
            yerr_t = np.std(self.curve_dict[dist][:, 0], axis=0) * (dist * dist)

            plt.plot(x, y, label="Sepreate output")
            plt.fill_between(x, y - yerr, y + yerr, alpha=0.5)

            # plt.plot(x, y_sep, label="Sepreate outputs")
            # plt.fill_between(x, y_sep - yerr_sep, y_sep + yerr_sep, alpha=0.5)

            # plt.plot(x, y_t, label="Training", linestyle='--')
            # plt.fill_between(x, y_t - yerr_t, y_t + yerr_t, alpha=0.5)

        # plt.yscale("log")

        plt.xlabel("epoch * 1000")
        plt.ylabel("loss")

        custom_ticks = np.arange(0.01, 0.004, 5)
        # plt.yticks(custom_ticks, [str(tick) for tick in custom_ticks])
        plt.legend()
        plt.title("Validation Loss")
        plt.tight_layout()
        plt.savefig("train_log_model/report/learning_curve.png")
        plt.show()

    def plot_images(self):
        seed = self.seeds[0]
        # short_dists = [0.8, 1.2]
        # cols = short_dists
        cols = self.dists
        rows = ['0', '1000', '10000', '100000', 'best', 'gt']
        rows_label = ['Epoch: 0', 'Epoch: 1k', 'Epoch: 10k', 'Epoch: 100k', 'Best Result', 'Ground Truth']
        cols_label = ['Distance = 800 mm', 'Distance = 1000 mm', 'Distance = 1200 mm']
        fig, axs = plt.subplots(len(rows), len(cols), sharex=True, sharey=True, figsize=(12, 6))
        fig.subplots_adjust(hspace=0.)
        # plt.style.use('seaborn')

        for i, dist in enumerate(cols):
            for j, row in enumerate(rows):

                path = "train_log_model/%s_id%d_%d(%d)_%s(%s)_cam%d(%d)" % ('sim', 0, 8000, seed, 'PE', 'arm', dist * 1000, seed) + "/image/%s.png" % row
                img = plt.imread(path)[:, :400, :]
                # print(img.shape)
                axs[j, i].imshow(img)
                # axs[j, i].axis('off')
                axs[j, i].set_xticks([])
                axs[j, i].set_yticks([])

        for ax, col in zip(axs[0], cols_label):
            ax.set_title(col, size='large')
        for ax, row in zip(axs[:,0], rows_label):
            ax.set_ylabel(row, rotation=0, labelpad=50) #  size='small'
        fig.tight_layout()
        plt.savefig("train_log_model/report/training.png")
        plt.show()

    def plot_results(self):
        dist_best_loss = []
        dist_best_tloss = []
        dist_best_loss_sep = []
        dist_best_tloss_sep = []
        for dist in self.dists:
            best_loss_long_seeds = np.min(self.curve_dict[dist][:, 1], axis=1) * dist * dist # shape: (3,)
            best_loss_mean = np.mean(best_loss_long_seeds)
            best_loss_std = np.std(best_loss_long_seeds)
            dist_best_loss.append((best_loss_mean, best_loss_std))

            best_tloss_long_seeds = np.min(self.curve_dict[dist][:, 0], axis=1) * dist * dist # shape: (3,)
            best_tloss_mean = np.mean(best_tloss_long_seeds)
            best_tloss_std = np.std(best_tloss_long_seeds)
            dist_best_tloss.append((best_tloss_mean, best_tloss_std))


            # best_tloss_long_seeds = np.min(self.curve_dict[dist+1][:, 1], axis=1) * dist * dist # shape: (3,)
            # best_tloss_mean = np.mean(best_tloss_long_seeds)
            # best_tloss_std = np.std(best_tloss_long_seeds)
            # dist_best_loss_sep.append((best_tloss_mean, best_tloss_std))


            # best_tloss_long_seeds = np.min(self.curve_dict[dist+1][:, 0], axis=1) * dist * dist # shape: (3,)
            # best_tloss_mean = np.mean(best_tloss_long_seeds)
            # best_tloss_std = np.std(best_tloss_long_seeds)
            # dist_best_tloss_sep.append((best_tloss_mean, best_tloss_std))


        # plt.figure(figsize=(12, 6))
        # plt.style.use('seaborn')
        # plt.style.use('seaborn-whitegrid')
        width = 0.1    # the width of the bars: can also be len(x) sequence
        fig, ax = plt.subplots(figsize=(8, 6))
        x = np.arange(len(self.dists))
        y = [loss for loss, _ in dist_best_loss]
        yerr = [std for _, std in dist_best_loss]
        yt = [loss for loss, _ in dist_best_tloss]
        yterr = [std for _, std in dist_best_tloss]

        # y_sep = [loss for loss, _ in dist_best_loss_sep]
        # yerr_sep = [std for _, std in dist_best_loss_sep]
        # yt_sep = [loss for loss, _ in dist_best_tloss_sep]
        # yterr_sep = [std for _, std in dist_best_tloss_sep]

        # np.savetxt("train_log_model/report/best_loss.txt", np.array([y, yerr, yt, yterr, y_sep, yerr_sep, yt_sep, yterr_sep]))

        # bar chart with error bars
        rects1 = ax.bar(x+width/2, y, yerr=yerr, capsize=5, label='Validation', width=width)
        rects2 = ax.bar(x-width/2, yt, yerr=yterr, capsize=5, label='Training', width=width)

        # rects3 = ax.bar(x+1+width/2, y_sep, yerr=yerr_sep, capsize=5, label='Validation (Sep)', width=width)
        # rects4 = ax.bar(x+1-width/2, yt_sep, yerr=yterr_sep, capsize=5, label='Training (Sep)', width=width)

        # plt.errorbar(x, y, yerr=yerr, fmt='o', capsize=5)
        # plt.xticks([0, 1], ["combined output", "separate outputs"])
        # plt.xlabel("Camera Distance (mm)")
        plt.xticks([0], [])
        plt.ylabel("MSE Loss")
        plt.title("Minimal Training Loss and Validation Loss (Separate Outputs)")
        
        plt.legend()
        plt.savefig("train_log_model/report/best_loss.png")
        plt.show()


if __name__ == "__main__":
    dists = [1.0]
    lc = LearningCurve(dists, 1, 100)  # plot epoches x-axis: start, end
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['savefig.dpi'] = 300
    lc.plot_curves()
    # lc.plot_images()
    lc.plot_results()

