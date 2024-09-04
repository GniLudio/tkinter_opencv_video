import tkinter
import multiprocessing, multiprocessing.connection
import cv2
import PIL.ImageTk, PIL.Image
import time
import math

class CV2Video:
    def __init__(self, container: tkinter.Label, filename_or_index: str | int, api_preference: int, flipped: bool, width: int | None, height: int | None, use_fps_delay: bool, frame_number: int = 0):
        self.container = container
        self.filename_or_index = filename_or_index
        self.api_preference = api_preference
        self.flipped = flipped
        self.width = width
        self.height = height
        self.use_fps_delay = use_fps_delay
        self.frame_number = frame_number

        self._frame_collector: multiprocessing.Process | None = None
        self._frame: cv2.typing.MatLike | None = None
        self._image: PIL.ImageTk.PhotoImage | None = None
        self._image_needs_update: bool = False

        if multiprocessing.current_process().name == "MainProcess":
            self.container.bind("<Configure>", func=lambda _: self.set_image_dirty(), add=True)

            (self._frame_receiver, self._frame_sender) = multiprocessing.Pipe(duplex=False)

            if isinstance(self.filename_or_index, str):
                self._collect_first_frame()
        else:
            self._frame_receiver = None
            self._frame_sender = None

    def play(self):
        if self._frame_collector is None:
            self._frame_collector = multiprocessing.Process(
                target=self._collect_frames, 
                args=(self._frame_sender, ),
                daemon=True
            )
            self._frame_collector.start()
            self.container.event_generate(sequence="<<PLAY>>")

    def pause(self):
        if self._frame_collector is not None:
            self.container.event_generate(sequence="<<PAUSE>>")
            self._frame_collector.terminate()
            self._frame_collector.join()
            self._frame_collector.close()
            self._frame_collector = None

    def toggle_play_pause(self):
        if self._frame_collector is None:
            self.play()
        else:
            self.pause()

    def reset(self):
        self.pause()
        self.frame_number = 0

    def update(self) -> bool:
        reached_end: bool = False
        while self._frame_receiver.poll():
            frame = self._frame_receiver.recv()
            if frame is not None:
                self._on_frame_received(frame)
            else:
                reached_end = True
        if self._image_needs_update:
            self._update_image()
        return not reached_end
    
    def set_image_dirty(self) -> None:
        self._image_needs_update = True

    def _on_frame_received(self, frame: cv2.typing.MatLike) -> None:
        self.frame_number += 1
        self._frame = frame
        self._image_needs_update = True

    def _collect_first_frame(self):
        """Collects the first frame."""
        try:
            capture = self._create_capture()
            success, frame = capture.read()
            if success:
                self._frame = frame
                self.set_image_dirty()
        finally:
            capture.release()

    def _collect_frames(self, sender: multiprocessing.connection.PipeConnection):
        """Continuously collects frames. Should be executed on a seperate process."""
        try:
            capture = self._create_capture()

            if self.use_fps_delay:
                duration_per_frame = 1 / (capture.get(cv2.CAP_PROP_FPS) or 1)
                next_frame_time = time.time()
            while not sender.closed:
                success, frame = capture.read()
                if success:
                    sender.send(frame)
                else:
                    sender.send(None)
                    break
                if self.use_fps_delay:
                    next_frame_time += duration_per_frame
                    duration_to_next_frame = next_frame_time - time.time()
                    if duration_to_next_frame > 0:
                        time.sleep(duration_to_next_frame)
        finally:
            capture.release()

    def _create_capture(self) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(self.filename_or_index, apiPreference=self.api_preference)
        if self.width is not None:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height is not None:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if self.frame_number > 0:
            capture.set(cv2.CAP_PROP_POS_FRAMES, self.frame_number)
        return capture

    def _update_image(self) -> None:
        self._image_needs_update = False
        if self._frame is not None:
            optimal_size = self._get_optimal_size()
            image = self._frame
            if self.flipped:
                image = cv2.flip(image, 1)
            image = cv2.resize(image,optimal_size)
            image = cv2.cvtColor(image,cv2.COLOR_BGR2RGBA)
            image = PIL.Image.fromarray(image)
            image = PIL.ImageTk.PhotoImage(image)
            self._image = image
        else:
            self._image = None
        self.container.configure(image=self._image)

    def _get_optimal_size(self) -> tuple[int, int]:
        max_width = self.container.winfo_width()
        max_height = self.container.winfo_height()
        video_aspect_ratio = self._frame.shape[1] / self._frame.shape[0]
        target_aspect_ratio = max_width / max_height
        if video_aspect_ratio == target_aspect_ratio:
            return (max_width, max_height)
        elif video_aspect_ratio < target_aspect_ratio:
            return (math.ceil(max_height * video_aspect_ratio), max_height)
        else:
            return (max_width, math.ceil(max_width / video_aspect_ratio))

    def __reduce__(self) -> str | tuple[object, ...]:
        return (self.__class__, (None, self.filename_or_index, self.api_preference, self.flipped, self.width, self.height, self.use_fps_delay, self.frame_number))

    def __del__(self):
        if self._frame_collector is not None:
            self._frame_collector.terminate()
            self._frame_collector.join()
            self._frame_collector.close()
        if self._frame_receiver is not None:
            self._frame_receiver.close()
        if self._frame_sender is not None:
            self._frame_sender.close()

def exit():
    global window_exited
    window_exited = True

if __name__ == '__main__':
    window = tkinter.Tk()
    window_exited = False
    window.protocol(name='WM_DELETE_WINDOW', func=exit)
    window.minsize(width=480, height=320)
    window.title("OpenCV video with tkinter")

    window.grid_rowconfigure(index=0, weight=1)
    window.grid_columnconfigure(index=0, weight=1)

    label = tkinter.Label(master=window, borderwidth=0, text="Loading")
    label.grid(row=0, column=0, sticky="nswe")

    # Webcam Example
    webcam = CV2Video(
        container=label,
        filename_or_index=0,
        api_preference=cv2.CAP_ANY,
        flipped=True,
        width=1920,
        height=1080,
        use_fps_delay=False,
    )
    webcam.play()

    # Video Example
    #video = CV2Video(
    #    container=label,
    #    filename_or_index="promi_s0_t0_l3.avi",
    #    api_preference=cv2.CAP_ANY,
    #    flipped=False,
    #    width=None,
    #    height=None,
    #    use_fps_delay=True,
    #)
    #video.play()

    while not window_exited:
        webcam.update()
        #video.update()
        window.update()
