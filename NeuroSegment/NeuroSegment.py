import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# NeuroSegment
#

class NeuroSegment(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NeuroSegment" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["John Doe (AnyWare Corp.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# NeuroSegmentWidget
#

class NeuroSegmentWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  NEURO_SEGMENT_WIDGET_LAYOUT_ID = 5612

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.logic = NeuroSegmentLogic()

    self.undockSliceViewButton = qt.QPushButton("Undock slice views")
    self.undockSliceViewButton.setCheckable(True)
    self.undockSliceViewButton.connect('clicked()', self.toggleSliceViews)
    self.layout.addWidget(self.undockSliceViewButton)

    self.panelLayout = qt.QHBoxLayout()
    self.layout.addLayout(self.panelLayout)

    # Load widget from .ui file (created by Qt Designer)
    segmentationPanel = slicer.util.loadUI(self.resourcePath('UI/SegmentationPanel.ui'))
    #segmentationPanel = slicer.modules.segmenteditor.widgetRepresentation()
    self.panelLayout.addWidget(segmentationPanel)
    self.segmentationUI = slicer.util.childWidgetVariables(segmentationPanel)
    segmentationPanel.setMRMLScene(slicer.mrmlScene)

    if (self.segmentationUI.segmentEditorWidget.mrmlSegmentEditorNode() is None):
      segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
      self.segmentationUI.segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)

    self.segmentationUI.segmentEditorWidget.connect("masterVolumeNodeChanged (vtkMRMLVolumeNode *)", self.onMasterVolumeNodeChanged)

    # Load widget from .ui file (created by Qt Designer)
    terminologyPanel = slicer.util.loadUI(self.resourcePath('UI/TerminologyPanel.ui'))
    self.panelLayout.addWidget(terminologyPanel)
    self.terminologyUI = slicer.util.childWidgetVariables(terminologyPanel)
    terminologyPanel.setMRMLScene(slicer.mrmlScene)

    # Add vertical spacer
    self.layout.addStretch(1)

    self.sliceViewWidget = None
    self.setupSliceViews()
    
    layoutManager = slicer.app.layoutManager()
    layoutManager.connect('layoutChanged(int)', self.onLayoutChanged)
    self.previousLayout = layoutManager.layout

  def setupSliceViews(self):
    layout = ("""
<layout type="horizontal">
 <item>
  <view class="vtkMRMLSliceNode" singletontag="Main">
   <property name="orientation" action="default">Axial</property>
     <property name="viewlabel" action="default">M</property>
   <property name="viewcolor" action="default">#808080</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLSliceNode" singletontag="Red">
   <property name="orientation" action="default">Axial</property>
     <property name="viewlabel" action="default">R</property>
   <property name="viewcolor" action="default">#F34A33</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLSliceNode" singletontag="Green">
   <property name="orientation" action="default">Axial</property>
   <property name="viewlabel" action="default">G</property>
   <property name="viewcolor" action="default">#6EB04B</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLSliceNode" singletontag="Yellow">
   <property name="orientation" action="default">Axial</property>
   <property name="viewlabel" action="default">Y</property>
   <property name="viewcolor" action="default">#EDD54C</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLViewNode" singletontag="1">
   <property name="viewlabel" action="default">1</property>
  </view>
 </item>
</layout>""")
    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(
      NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID, layout)

  def cleanup(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.disconnect('layoutChanged(int)', self.onLayoutChanged)

  def toggleSliceViews(self):
    if self.undockSliceViewButton.checked:
      slicer.app.layoutManager().setLayout(NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID)
    else:
      slicer.app.layoutManager().setLayout(self.previousLayout)

  def onLayoutChanged(self, layoutID):
    if layoutID != NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID and self.sliceViewWidget:
      self.previousLayout = layoutID
      self.sliceViewWidget.close()

    elif layoutID == NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID:
      self.sliceViewWidget = qt.QSplitter(qt.Qt.Horizontal)

      self.mainViewPanel = qt.QWidget()
      mainPanelLayout = qt.QHBoxLayout()
      self.mainViewPanel.setLayout(mainPanelLayout)
      mainPanelLayout.addWidget(slicer.app.layoutManager().sliceWidget('Main'))
      self.mainViewPanel.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
      self.sliceViewWidget.addWidget(self.mainViewPanel)

      self.secondaryViewPanel = qt.QWidget()
      rightPanelLayout = qt.QVBoxLayout()
      self.secondaryViewPanel.setLayout(rightPanelLayout)
      rightPanelLayout.addWidget(slicer.app.layoutManager().sliceWidget('Red'))
      rightPanelLayout.addWidget(slicer.app.layoutManager().sliceWidget('Green'))
      rightPanelLayout.addWidget(slicer.app.layoutManager().sliceWidget('Yellow'))
      self.sliceViewWidget.addWidget(self.secondaryViewPanel)

      # Find the first screen that is not the main screen
      # Otherwise default to the main screen
      mainScreen = slicer.util.mainWindow().windowHandle().screen()
      widgetScreen = mainScreen
      screens = slicer.app.screens()
      if len(screens) > 1:
        for screen in screens:
          if mainScreen != screen:
            widgetScreen = screen
            break

      self.sliceViewWidget.show()
      self.sliceViewWidget.windowHandle().setScreen(widgetScreen)     
      self.sliceViewWidget.showFullScreen() # Will not move to the other monitor with just setScreen. showFullScreen moves the window
      self.sliceViewWidget.showMaximized()

  def onMasterVolumeNodeChanged(self, volumeNode):
    self.segmentationUI.volumeThresholdWidget.setMRMLVolumeNode(volumeNode)
    self.segmentationUI.windowLevelWidget.setMRMLVolumeNode(volumeNode)

  def showSingleModule(self, singleModule=True, toggle=False):

    if toggle:
      singleModule = not self.isSingleModuleShown

    self.isSingleModuleShown = singleModule

    if singleModule:
      # We hide all toolbars, etc. which is inconvenient as a default startup setting,
      # therefore disable saving of window setup.
      import qt
      settings = qt.QSettings()
      settings.setValue('MainWindow/RestoreGeometry', 'false')

    keepToolbars = [
      slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'ViewToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'ViewersToolBar')]
    slicer.util.setToolbarsVisible(not singleModule, keepToolbars)
    slicer.util.setMenuBarsVisible(not singleModule)
    slicer.util.setApplicationLogoVisible(not singleModule)
    slicer.util.setModuleHelpSectionVisible(not singleModule)
    slicer.util.setModulePanelTitleVisible(not singleModule)
    slicer.util.setDataProbeVisible(not singleModule)
    slicer.util.setViewControllersVisible(not singleModule)

    if singleModule:
      slicer.util.setPythonConsoleVisible(False)

#
# NeuroSegmentLogic
#

class NeuroSegmentLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def hasImageData(self,volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True

  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    if not self.isValidInputOutputData(inputVolume, outputVolume):
      slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
      return False

    logging.info('Processing started')

    # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
    cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(), 'ThresholdValue' : imageThreshold, 'ThresholdType' : 'Above'}
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

    # Capture screenshot
    if enableScreenshots:
      self.takeScreenshot('NeuroSegmentTest-Start','MyScreenshot',-1)

    logging.info('Processing completed')

    return True


class NeuroSegmentTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_NeuroSegment1()

  def test_NeuroSegment1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import SampleData
    SampleData.downloadFromURL(
      nodeNames='FA',
      fileNames='FA.nrrd',
      uris='http://slicer.kitware.com/midas3/download?items=5767')
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = NeuroSegmentLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
