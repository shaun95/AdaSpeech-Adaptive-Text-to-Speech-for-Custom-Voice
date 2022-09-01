import torch, os
from model.pl_model import PL_model
import pytorch_lightning as pl
import pytorch_lightning.callbacks as plc
from pytorch_lightning.loggers import TensorBoardLogger
from torch.utils.data import DataLoader
from pytorch_lightning.callbacks import LearningRateMonitor
from pytorch_lightning.strategies import DDPStrategy
import yaml
from dataset import Dataset

def main(train_config, preprocess_config, model_config):
    pl.seed_everything(42)
    num_gpu = torch.cuda.device_count()

    model = PL_model(
        train_config,
        preprocess_config,
        model_config,
    )

    train_dataset = Dataset(
        "train.txt", preprocess_config, train_config, sort=True, drop_last=True
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=train_config['optimizer']['batch_size'],
        shuffle=False,
        collate_fn=train_dataset.collate_fn,
        drop_last=True,
        num_workers=8
    )

    val_dataset = Dataset(
        "val.txt", preprocess_config, train_config, sort=True, drop_last=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=train_config['optimizer']['batch_size'],
        shuffle=False,
        collate_fn=val_dataset.collate_fn,
        drop_last=True,
        num_workers=8
    )
    setattr(model, 'train_dataloader', lambda: train_loader)
    setattr(model, 'val_dataloader', lambda: val_loader)

    checkpoint_callback = plc.ModelCheckpoint(
        monitor="step",
        dirpath=os.path.join(train_config['path']['ckpt_path'], train_config['path']['exp_name']),
        filename="{step:06d}",
        save_top_k=10,
        mode="max",
        every_n_train_steps=train_config['step']['save_step']
    )

    logger = TensorBoardLogger(
        train_config['path']['log_path'], name=train_config['path']['exp_name'])
    lr_monitor = LearningRateMonitor(logging_interval='step')
    
    trainer = pl.Trainer(
        accelerator="gpu",
        devices=num_gpu,
        strategy = DDPStrategy(find_unused_parameters=False),
        max_steps=train_config['step']['total_step'],
        enable_checkpointing=True,
        callbacks=[checkpoint_callback, lr_monitor],
        profiler="simple",
        accumulate_grad_batches=train_config['trainer']['grad_acc'],
        logger=logger,
        gradient_clip_val=train_config['trainer']['grad_clip_thresh']
    )
    trainer.fit(model)
    
if __name__ == '__main__':
    train_config = yaml.load(
        open("./config/visual_novel/train.yaml", "r"), Loader=yaml.FullLoader
    )
    preprocess_config = yaml.load(
        open("./config/visual_novel/preprocess.yaml", "r"), Loader=yaml.FullLoader
    )
    model_config = yaml.load(
        open("./config/visual_novel/model.yaml", "r"), Loader=yaml.FullLoader
    )
    main(train_config, preprocess_config, model_config)