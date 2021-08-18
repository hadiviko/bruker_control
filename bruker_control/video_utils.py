# Bruker 2-Photon Video Utils
# Jeremy Delahanty May 2021
# Harvesters written by Kazunari Kudo
# https://github.com/genicam/harvesters

###############################################################################
# Import Packages
###############################################################################

# Teledyne DALSA Genie Nano Interface: Harvesters
from harvesters.core import Harvester

# Import OpenCV2 to write images/videos to file + previews
import cv2

# Import datetime for filenaming
from datetime import datetime

# Import Tuple for appropriate typehinting of functions
from typing import Tuple

# Import tqdm for progress bar
from tqdm import tqdm

# Static cti file location
cti_filepath = "C:/Program Files/MATRIX VISION/mvIMPACT Acquire/bin/x64/mvGENTLProducer.cti"

# Experiment videos are written to the Raw Data volume on the machine BRUKER
# which is mounted to E:
basepath = "E:/"

###############################################################################
# Video Exception Creation
###############################################################################


class CameraNotFound(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        print("calling str")
        if self.message:
            return "MyCustomError, {0} ".format(self.message)
        else:
            return "Custom Error has been raised"


###############################################################################
# Camera Control
###############################################################################

# -----------------------------------------------------------------------------
# Initiate Preview Camera
# -----------------------------------------------------------------------------


def init_camera_preview() -> Tuple[Harvester, Harvester, int, int]:
    """
    Creates, configures, describes, and starts harvesters camera object in
    preview setting.

    Initializes harvester camera, sets camera properties appropriate for
    preview, gathers the camera's width and height in pixels, and starts
    video acquisition. The function takes no arguments.

    Returns:

        Harvester object

        Camera object

        Camera's height (pixels)

        Camera's width (pixels)

    """

    # Create camera variable as None type
    camera = None

    # Create harvester object as h
    h = Harvester()

    # Give path to GENTL producer
    cti_file = cti_filepath

    # Add GENTL producer to Harvester object
    h.add_file(cti_file)

    # Update Harvester object
    h.update()

    # Print device list to make sure camera is present
    # TODO: Raise an error if no camera is detected
    print("Connected to Camera: \n", h.device_info_list)

    # Grab Camera, Change Settings
    # Create image_acquirer object for Harvester, grab first (only) device
    camera = h.create_image_acquirer(0)

    # Gather node map to camera properties
    n = camera.remote_device.node_map

    # Save camera width and height parameters
    width = n.Width.value
    height = n.Height.value

    # Change camera properties for continuous recording, no triggers needed
    n.AcquisitionMode.value = "Continuous"
    n.TriggerMode.value = "Off"

    # Show user the preview acquisition mode
    print("Preview Mode:", n.AcquisitionMode.value)

    # Start the acquisition
    print("Starting Preview")
    camera.start_acquisition()

    # Return harvester, camera, and width/height in pixels of camera
    return h, camera, width, height


# -----------------------------------------------------------------------------
# Capture Preview of Camera
# -----------------------------------------------------------------------------


def capture_preview():
    """
    Capture frames generated by camera object and display them in preview mode.

    Takes values from init_camera_preview() to capture images delivered by
    camera buffer, reshapes the image to appropriate height and width, and
    finally displays the image to an opencv window. When user hits the 'Esc'
    key, the window closes and the camera object is destroyed. This function
    takes no arguments and returns nothing.

    """

    h, camera, width, height = init_camera_preview()
    preview_status = True
    print("To stop preview, hit 'Esc' key")
    while preview_status is True:
        try:
            with camera.fetch_buffer() as buffer:
                # Define frame content with buffer.payload
                content = buffer.payload.components[0].data.reshape(height,
                                                                    width)

                # Provide preview for camera contents:
                cv2.imshow("Preview", content)
                c = cv2.waitKey(1) % 0x100
                if c == 27:
                    preview_status = False

        except:
            pass

    cv2.destroyAllWindows()

    # Shutdown the camera
    shutdown_camera(camera, h)


# -----------------------------------------------------------------------------
# Initialize Camera for Recording
# -----------------------------------------------------------------------------


def init_camera_recording() -> Tuple[Harvester, Harvester, int, int]:
    """
    Creates, configures, describes, and starts harvesters camera object in
    recording setting.

    Initializes harvester camera, sets camera properties appropriate for
    behavior recording, gathers the camera's width and height in pixels, and
    starts video acquisition. There are no arguments.

    Returns:

        Harvester object

        Camera object

        Camera's height (pixels)

        Camera's width (pixels)
    """

    camera = None

    # Setup Harvester
    # Create harvester object as h
    h = Harvester()

    # Give path to GENTL producer
    cti_file = cti_filepath

    # Add GENTL producer to Harvester object
    h.add_file(cti_file)

    # Update Harvester object
    h.update()

    # Print device list to make sure camera is present
    print("Connected to Camera: \n", h.device_info_list)

    # Grab Camera, Change Settings
    # Create image_acquirer object for Harvester, grab first (only) device
    camera = h.create_image_acquirer(0)

    # Gather node map to camera properties
    n = camera.remote_device.node_map

    # Set and then save camera width and height parameters
    width = n.Width.value  # width = 1280
    height = n.Height.value  # height = 1024

    # Change camera properties to listen for Bruker TTL triggers
    # Record continuously
    n.AcquisitionMode.value = "Continuous"

    # Listen for Bruker's TTL triggers
    n.TriggerMode.value = "On"

    # Trigger camera on rising edge of input signal
    n.TriggerActivation.value = "RisingEdge"

    # Select Line 2 as the Trigger Source and Input Source
    n.TriggerSource.value = "Line2"
    n.LineSelector.value = "Line2"

    # Print in terminal which acquisition mode is enabled
    print("Acquisition Mode: ", n.AcquisitionMode.value)

    # Start the acquisition, return camera and harvester for buffer
    print("Starting Acquisition")
    camera.start_acquisition()

    # Return Harvester, camera, and frame dimensions
    return h, camera, width, height


# -----------------------------------------------------------------------------
# Capture Camera Recording
# -----------------------------------------------------------------------------


def capture_recording(num_frames: int, imaging_plane: str, team: str,
                      subject_id: str) -> list:
    """
    Capture frames generated by camera object, display them in recording mode,
    and write frames to .avi file.

    Takes values from init_camera_recording() to capture images delivered by
    camera buffer, reshapes the image to appropriate height and width, displays
    the image to an opencv window, and writes the image to a .avi file.
    When the camera acquires the specified number of frames for an experiment,
    the window closes, the camera object is destroyed, and the video is written
    to disk.

    Args:
        number_frames:
            Number of frames specified to collect for the video recording
        imaging_plane:
            Plane the 2P image is currently being taken acquired from Prairie
            View
        team:
            The team performing the experiment
        subject_id:
            The subject being recorded

    Returns:
        dropped_frames
    """

    # Gather session date using datetime
    session_date = datetime.today().strftime("%Y%m%d")

    # Set microscopy session's path
    video_dir = basepath + team + "/video/"

    # Set session name by joining variables with underscores
    session_name = "_".join([session_date, subject_id,
                             "plane{}".format(imaging_plane)])

    # Assign video name as the config_filename for readability
    video_name = session_name + ".avi"

    # Create full video path
    video_fullpath = video_dir + video_name

    # Define video codec for writing images
    fourcc = cv2.VideoWriter_fourcc(*'DIVX')

    # Start the Camera
    # h, camera, width, height = init_camera_recording()

    # Create VideoWriter object: file, codec, framerate, dims, color value
    # out = cv2.VideoWriter(video_fullpath, fourcc, 30, (width, height),
    #                       isColor=False)

    dropped_frames = []

    frame_number = 1

    for frame in tqdm(range(num_frames), desc="Experiment Progress"):

        # Introduce try/except block in case of dropped frames
        try:

            # Use with statement to acquire buffer, payload, an data
            # Payload is 1D numpy array, RESHAPE WITH HEIGHT THEN WIDTH
            # Numpy is backwards, reshaping as heightxwidth writes correctly
            # with camera.fetch_buffer() as buffer:

            # Define frame content with buffer.payload
            # content = buffer.payload.components[0].data.reshape(height, width)

            # Debugging statment, print content shape and frame number
            # print(content.shape)
            # print(frame_number)
            # out.write(content)
            # cv2.imshow("Live", content)
            # cv2.waitKey(1)

            frame_number += 1

        # # TODO Raise warning for frame drops
        except:
            dropped_frames.append(frame_number)
            frame_number += 1
            pass

    # Release VideoWriter object
    # out.release()
    #
    # # Destroy camera window
    # cv2.destroyAllWindows()
    #
    # # Shutdown the camera
    # shutdown_camera(camera, h)

    return dropped_frames

# -----------------------------------------------------------------------------
# Shutdown Camera
# -----------------------------------------------------------------------------


def shutdown_camera(camera: Harvester, harvester: Harvester):
    """
    Deactivates and resets both harvester and camera after acquisition.

    Turns off camera, resets its configuration values, and resets the harvester
    object once acquisition is done. The function does not return anything

    Args:
        camera
            Harverster camera object
        harvester
            Haverster object
    """

    # Stop the camera's acquisition
    print("Stopping Acquisition")
    camera.stop_acquisition()

    # Destroy the camera object, release the resource
    print("Camera Destroyed")
    camera.destroy()

    # Reset Harvester object
    print("Resetting Harvester")
    camera.reset()


def calculate_frames(session_len_s: int) -> int:
    """
    Calculates number of images to collect during the experiment.

    Converts imaging session length into number of frames to collect by
    microscope and, therefore, camera.

    Args:
        session_len_s:
            Experimental session length in seconds

    Returns:
        num_frames
    """

    # Generate buffer of 300 images to ensure enough data is captured when
    # session ends.
    imaging_buffer = 300

    # Calculate number of video frames
    video_frames = (round(session_len_s)*30) + imaging_buffer

    return video_frames
