
6 png files ->xc-enc-> on Y4M file

png files are from [Xiph](https://media.xiph.org/sintel/sintel-1k-png16/)

building `daala_tools` also requires headers from `xiph/ogg`. Install the `xiph/ogg` library using this repo: https://github.com/xiph/ogg

[More information about the daala project](https://wiki.xiph.org/Daala_Quickstart)


`.y4m` are YUV4MPEG2 Video Files. They store a sequence of uncompressed YCbCr
images that make up the video frame by frame. They are often used as a raw,
color-sensitive video format before compressing into a more popular video format
such as MPEG-2.

More information about `vpxenc`: https://www.webmproject.org/docs/encoder-parameters/

# Process

6 uncompressed images from `sintel-1k` --> png2y4m --> video.y4m

The y4m video file = 6 frames of raw video meaning uncompressed images. There is
no keyframes vs interframes in y4m files






video.y4m--> vpxenc --> video.vp8 or video.ivf

The `vp8` file = 1 keyframe followed by 5 interframes

How to run vpxenc??


`mu/src/lambdaize/vpxenc_server.py`:

The VPXEncStateMachine has a `commandlist`. from the command list, we can see that the outputfile has suffix `.ivf`.

`mu/src/lambdaize/vpx_ssim_server.py`:

`vpx_cmdstring = "./vpxenc -y --codec=vp8 --ivf --min-q=##QUALITY## --max-q=##QUALITY## -o ##OUTFILE##_##QUALITY## ##INFILE##"`

`-y`: display warnings

`--codec=vp8`: codec to use

`--ivf`: output IVF

`--min-q`: let's use 0 

`--max-q`: let's use 16?? From `
mu/src/lambdaize/vpx_ssim_server.py` `quality_values`.



In the command list, there are 4 commands:

`./xc-framesize ##OUTFILE##_##QUALITY## >> ##TMPDIR##/{1}.txt`

`./vpxdec --codec=vp8 -o ##INFILE##_dec_##QUALITY## ##OUTFILE##_##QUALITY##`

`./dump_ssim ##INFILE## ##INFILE##_dec_##QUALITY## >> ##TMPDIR##/{1}.txt`

`rm ##INFILE##_dec_##QUALITY## ##OUTFILE##_##QUALITY##`



# Testing

Need the alfalfa repo.

```bash
apt install yasm x264 libx264-dev libjpeg9-dev freeglut3-dev libglfw3-dev libglfw3-dev libglew-dev libboost-all-dev
```

The command to concatenate ivf files:

```bash
ls *.ivf | ./alfalfa/src/frontend/xc-decode-bundle > video.ivf
```



# Input

We have 2 options:

1. An array of S3 pointers
2. Use S3 ObjectCreated event



https://excamera-us-west-2.s3-us-west-2.amazonaws.com/sintel-1k-y4m_06/00000000.y4m