# Importing relevant Libraries
import torch
import torch.nn as nn

class DCGAN(nn.Module):
    def __init__(self, filter_size=64):
        super(DCGAN, self).__init__()
        self.name = "DC-GAN"
        self.netD = Discriminator(filter_size=filter_size)
        self.netG = Generator(num_downsampling=8, filter_size=filter_size)

class Discriminator(nn.Module):
    def __init__(self, filter_size=64):
        super(Discriminator, self).__init__()
        self.name = "Discriminator"
        self.filter_size = filter_size
        self.layer1 = nn.Sequential(
            nn.Conv2d(6, self.filter_size, kernel_size=4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True)
        )
        self.layer2 = nn.Sequential(
            nn.Conv2d(self.filter_size, self.filter_size*2, kernel_size=4, stride=2, padding=1),
            nn.InstanceNorm2d(self.filter_size*2),
            nn.LeakyReLU(0.2, inplace=True)
        )
        self.layer3 = nn.Sequential(
            nn.Conv2d(self.filter_size * 2, self.filter_size * 4, kernel_size=4, stride=2, padding=1),
            nn.InstanceNorm2d(self.filter_size * 4),
            nn.LeakyReLU(0.2, inplace=True)
        )
        self.layer4 = nn.Sequential(
            nn.Conv2d(self.filter_size * 4, self.filter_size * 8, kernel_size=4, stride=1, padding=1),
            nn.InstanceNorm2d(self.filter_size * 8),
            nn.LeakyReLU(0.2, inplace=True)
        )
        self.layer5 = nn.Sequential(
            nn.Conv2d(self.filter_size * 8, 1, kernel_size=4, stride=1, padding=1),
            nn.Sigmoid()
        )

    def forward(self, input, label):
        x = torch.cat([input, label], 1)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        return x

# Take sketch of lines as input, and output a generated image
class Generator(nn.Module):
    """
    An eight hidden-layer generative neural network
    """
    def __init__(self, num_downsampling=8, filter_size=64):
        super(Generator, self).__init__()
        self.name = "Generator"
        self.model = Unet(num_downsampling=num_downsampling, filter_size=filter_size)

    def forward(self, x):
        x = self.model(x)
        return x

# Recursive Unet implementation from
# https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix/blob/master/models/networks.py
class Unet(nn.Module):
    def __init__(self, num_downsampling=8, filter_size=64):
        super(Unet, self).__init__()
        # innermost layer
        unet_block = UnetBlock(filter_size * 8, filter_size * 8, None, innermost=True)
        # intermediate layers
        for i in range(num_downsampling - 5):
            unet_block = UnetBlock(filter_size * 8, filter_size * 8, None, unet_block)
        # downsampling and upsampling layers
        unet_block = UnetBlock(filter_size * 8, filter_size * 4, None, unet_block)
        unet_block = UnetBlock(filter_size * 4, filter_size * 2, None, unet_block)
        unet_block = UnetBlock(filter_size * 2, filter_size, None, unet_block)
        # outermost layer
        self.model = UnetBlock(filter_size, 3, 3, unet_block, outermost=True)

    def forward(self, input):
        return self.model(input)

# Unet Blocks that uses skip connection
class UnetBlock(nn.Module):
    # in_channel and out_channel are naming from transposed convolution side
    def __init__(self, in_channel, out_channel, input_channel=None, subnet=None, outermost=False, innermost=False):
        super(UnetBlock, self).__init__()
        self.outermost = outermost
        if input_channel is None:
            input_channel = out_channel
        downconv = nn.Conv2d(input_channel, in_channel, kernel_size=4, stride=2, padding=1)
        downrelu = nn.LeakyReLU(0.2, inplace=True)
        downnorm = nn.InstanceNorm2d(in_channel)
        uprelu = nn.ReLU(inplace=True)
        upnorm = nn.InstanceNorm2d(out_channel)

        if innermost:
            upconv = nn.ConvTranspose2d(in_channel, out_channel, kernel_size=4, stride=2, padding=1)
            down = [downrelu, downconv]
            up = [uprelu, upconv, upnorm]
            model = down + up
        elif outermost:
            upconv = nn.ConvTranspose2d(in_channel * 2, out_channel, kernel_size=4, stride=2, padding=1)
            down = [downconv]
            up = [uprelu, upconv, nn.Tanh()]
            model = down + [subnet] + up
        else:
            upconv = nn.ConvTranspose2d(in_channel * 2, out_channel, kernel_size=4, stride=2, padding=1)
            down = [downrelu, downconv, downnorm]
            up = [uprelu, upconv, upnorm]
            model = down + [subnet] + up

        self.model = nn.Sequential(*model)

    def forward(self, x):
        if self.outermost:
            return self.model(x)
        else:
            return torch.cat([x, self.model(x)], 1)