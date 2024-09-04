# TKinter OpenCV Video

Utility class for displaying OpenCV videos with Tkinter.

## Features
* Automatic resizing of the video when the window size changes.
* Playback speed respecting the video's frame rate.
* Expands video to optimal size.
  * Respecting the videos aspect ratio.
  * Supporting expanding.
* Grabs all frames.
  * Indepedent of the performance of your main-thread and/or main-process.
  * Useful if you want to further process the images. (e.g. for saving the webcam feed)
* Only updates image if necessary.

## Remarks
Starting a webcam feed can take some time. (a few seconds)

The `borderwidth` of the tkinter label should be `0`.

For faster play/pause response times, the frame-collector process would need to be changed:
Instead of restarting the process on time, the process would need to listen permanently to play and pause.
