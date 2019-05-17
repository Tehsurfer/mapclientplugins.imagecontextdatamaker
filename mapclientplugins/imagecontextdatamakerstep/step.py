
"""
MAP Client Plugin Step
"""
import re
import json
import imagesize

import cv2
import io
from PIL import Image

from PySide import QtGui, QtCore

from opencmiss.zinc.context import Context
from opencmiss.utils.zinc import createFiniteElementField, createSquare2DFiniteElement,\
    createVolumeImageField, createMaterialUsingImageField
from opencmiss.zincwidgets.basesceneviewerwidget import BaseSceneviewerWidget

from mapclient.mountpoints.workflowstep import WorkflowStepMountPoint
from mapclientplugins.imagecontextdatamakerstep.configuredialog import ConfigureDialog

class ImageContextData(object):

    def __init__(self, context, frames_per_second, image_file_names, image_dimensions, video_path):
        self._context = context
        self._shareable_widget = BaseSceneviewerWidget()
        self._shareable_widget.set_context(context)
        self._frames_per_second = frames_per_second
        self._image_file_names = image_file_names
        self._image_dimensions = image_dimensions
        self._video_path = video_path

    def get_context(self):
        return self._context

    def get_video_path(self):
        return self._video_path

    def get_shareable_open_gl_widget(self):
        return self._shareable_widget

    def get_frames_per_second(self):
        return self._frames_per_second

    def get_frame_count(self):
        return len(self._image_file_names)

    def get_image_file_names(self):
        return self._image_file_names

    def get_image_dimensions(self):
        return self._image_dimensions


class ImageContextDataMakerStep(WorkflowStepMountPoint):
    """
    Skeleton step which is intended to be a helpful starting point
    for new steps.
    """

    def __init__(self, location):
        super(ImageContextDataMakerStep, self).__init__('Image Context Data Maker', location)
        self._configured = False # A step cannot be executed until it has been configured.
        self._category = 'Utility'
        # Add any other initialisation code here:
        self._icon =  QtGui.QImage(':/imagecontextdatamakerstep/images/utility.png')
        # Ports:
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#provides',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#image_context_data'))
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#uses',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#file_location'))
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#uses',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#images'))
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#provides',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#2d_image_dimension'))
        # Port data:
        self._portData0 = None  # http://physiomeproject.org/workflow/1.0/rdf-schema#image_context_data
        self._portData1 = None  # http://physiomeproject.org/workflow/1.0/rdf-schema#file_location
        self._portData2 = None  # http://physiomeproject.org/workflow/1.0/rdf-schema#images
        self._portData3 = None  # http://physiomeproject.org/workflow/1.0/rdf-schema#2d_image_dimension
        # Config:
        self._config = {'identifier': '', 'frames_per_second': 30}

    def execute(self):
        """
        Add your code here that will kick off the execution of the step.
        Make sure you call the _doneExecution() method when finished.  This method
        may be connected up to a button in a widget for example.
        """
        # Put your execute step code here before calling the '_doneExecution' method.
        context = Context('images')
        region = create_model(context)
        # Must put a note on the config that this doesn't apply to video feeds.
        frames_per_second = self._config['frames_per_second']

        if self._portData2 is not None: # Note that this is currently an old unused method of loading video
            image_file_names = self._portData2.image_files()
            image_dimensions, _ = _load_images(image_file_names, frames_per_second, region)
            image_context_data = ImageContextData(context, frames_per_second, image_file_names, image_dimensions)
        elif self._portData1 is not None:


            image_frames, image_dimensions, frames_per_second = frameFromVideo(self._portData1) # Figure out video details
            creatZincFields(region, image_frames, frames_per_second, image_dimensions)
            image_context_data = ImageContextData(context, frames_per_second, image_frames,
                                                  image_dimensions, self._portData1)
        else:
            Exception('One of these ports should have data connected.')

        self._portData0 = image_context_data
        self._portData3 = image_dimensions
        self._doneExecution()

    def setPortData(self, index, dataIn):
        """
        Add your code here that will set the appropriate objects for this step.
        The index is the index of the port in the port list.  If there is only one
        uses port for this step then the index can be ignored.

        :param index: Index of the port to return.
        :param dataIn: The data to set for the port at the given index.
        """
        if index == 1:
            self._portData1 = dataIn  # http://physiomeproject.org/workflow/1.0/rdf-schema#file_location
        elif index == 2:
            self._portData2 = dataIn  # http://physiomeproject.org/workflow/1.0/rdf-schema#images

    def getPortData(self, index):
        """
        Add your code here that will return the appropriate objects for this step.
        The index is the index of the port in the port list.  If there is only one
        provides port for this step then the index can be ignored.

        :param index: Index of the port to return.
        """
        port_data = self._portData0  # image_context_data
        if index == 3:
            port_data = self._portData3  # 2d_image_dimension

        return port_data

    def configure(self):
        """
        This function will be called when the configure icon on the step is
        clicked.  It is appropriate to display a configuration dialog at this
        time.  If the conditions for the configuration of this step are complete
        then set:
            self._configured = True
        """
        # dlg = ConfigureDialog(self._main_window)
        dlg = ConfigureDialog()
        dlg.identifierOccursCount = self._identifierOccursCount
        dlg.setConfig(self._config)
        dlg.validate()
        dlg.setModal(True)

        if dlg.exec_():
            self._config = dlg.getConfig()

        self._configured = dlg.validate()
        self._configuredObserver()

    def getIdentifier(self):
        """
        The identifier is a string that must be unique within a workflow.
        """
        return self._config['identifier']

    def setIdentifier(self, identifier):
        """
        The framework will set the identifier for this step when it is loaded.
        """
        self._config['identifier'] = identifier

    def serialize(self):
        """
        Add code to serialize this step to string.  This method should
        implement the opposite of 'deserialize'.
        """
        return json.dumps(self._config, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def deserialize(self, string):
        """
        Add code to deserialize this step from string.  This method should
        implement the opposite of 'serialize'.

        :param string: JSON representation of the configuration in a string.
        """
        self._config.update(json.loads(string))

        d = ConfigureDialog()
        d.identifierOccursCount = self._identifierOccursCount
        d.setConfig(self._config)
        self._configured = d.validate()


def create_model(context):
    default_region = context.getDefaultRegion()
    region = default_region.createChild('images')
    coordinate_field = createFiniteElementField(region)
    field_module = region.getFieldmodule()
    scale_field = field_module.createFieldConstant([2, 3, 1])
    scale_field.setName('scale')
    duration_field = field_module.createFieldConstant(1.0)
    duration_field.setManaged(True)
    duration_field.setName('duration')
    offset_field = field_module.createFieldConstant([+0.5, +0.5, 0.0])
    scaled_coordinate_field = field_module.createFieldMultiply(scale_field, coordinate_field)
    scaled_coordinate_field = field_module.createFieldAdd(scaled_coordinate_field, offset_field)
    scaled_coordinate_field.setManaged(True)
    scaled_coordinate_field.setName('scaled_coordinates')
    createSquare2DFiniteElement(field_module, coordinate_field,
                                    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]])

    return region


def frameFromVideo(filename):
    cap = cv2.VideoCapture(filename)
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    imageList = list()
    while not cap.isOpened():
        cap = cv2.VideoCapture(filename)
        cv2.waitKey(1000)
        print("Wait for the header")
    posFrame = cap.get(cv2.CAP_PROP_POS_FRAMES)
    count = 1
    while True:
        flag, frame = cap.read()
        if flag and count != length:
            if count == 1:
                imageDimension = [frame.shape[1], frame.shape[0]]
            imageList.append('unused')
        else:
            break
        count+=1
    if len(imageList) > 0:
        imageList.pop()
    cap.release()
    return imageList, imageDimension, fps

def creatZincFields(region, images, frames_per_second, image_dimension):
    image_dimensions = [-1, -1]
    field_module = region.getFieldmodule()
    frame_count = len(images)
    # Assume all images have the same dimensions.
    width, height = image_dimension
    cache = field_module.createFieldcache()
    scale_field = field_module.findFieldByName('scale')
    scale_field.assignReal(cache, [width, height, 1.0])
    duration = frame_count / frames_per_second
    duration_field = field_module.findFieldByName('duration')
    duration_field.assignReal(cache, duration)
    image_dimensions = [width, height]
    image_field = createVolumeImageField(field_module, image_dimension)
    image_based_material = createMaterialUsingImageField(region, image_field)
    image_based_material.setName('images') # this is where we will grab the material later
    image_based_material.setManaged(True)
    return image_dimensions, image_based_material

def createVolumeImageField(fieldmodule, image_dims, field_name='volume_image'):
    """
    Create an image field using the given fieldmodule.  The image filename must exist and
    be a known image type.

    :param fieldmodule: The fieldmodule to create the field in.
    :param buffer: image buffers
    :param field_name: Optional name of the image field, defaults to 'volume_image'.
    :return: The image field created.
    """
    image_field = fieldmodule.createFieldImage()
    image_field.setName(field_name)
    image_field.setFilterMode(image_field.FILTER_MODE_LINEAR)
    image_field.setSizeInPixels([image_dims[0], image_dims[1], 1])
    image_field.setPixelFormat(image_field.PIXEL_FORMAT_BGR)

    return image_field








# ----- Old functions be below this point ----

def _load_images(images, frames_per_second, region):
    field_module = region.getFieldmodule()
    frame_count = len(images)
    image_dimensions = [0, 0]
    image_based_material = None
    if frame_count > 0:
        # Assume all images have the same dimensions.
        width, height = imagesize.get(images[0])
        if width != -1 or height != -1:
            cache = field_module.createFieldcache()
            scale_field = field_module.findFieldByName('scale')
            scale_field.assignReal(cache, [width, height, 1.0])
            duration = frame_count / frames_per_second
            duration_field = field_module.findFieldByName('duration')
            duration_field.assignReal(cache, duration)
            image_dimensions = [width, height]
        image_field = createVolumeImageField(field_module, images)
        image_based_material = createMaterialUsingImageField(region, image_field)
        image_based_material.setName('images')
        image_based_material.setManaged(True)

    return image_dimensions, image_based_material


def _get_images(images, frames_per_second, region, image_dimension):
    image_dimensions = [-1, -1]
    field_module = region.getFieldmodule()
    frame_count = len(images)
    if frame_count > 0:
        # Assume all images have the same dimensions.
        width, height = image_dimension
        if width != -1 or height != -1:
            cache = field_module.createFieldcache()
            scale_field = field_module.findFieldByName('scale')
            scale_field.assignReal(cache, [width, height, 1.0])
            duration = frame_count / frames_per_second
            duration_field = field_module.findFieldByName('duration')
            duration_field.assignReal(cache, duration)
            image_dimensions = [width, height]
    image_field = createVolumeImageField(field_module, images)
    image_based_material = createMaterialUsingImageField(region, image_field)
    image_based_material.setName('images') # this is where we will grab the material later
    image_based_material.setManaged(True)
    return image_dimensions, image_based_material