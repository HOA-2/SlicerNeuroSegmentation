import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin

#
# NeuroSegment
#

class NeuroSegment(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NeuroSegment"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = []
    self.parent.contributors = ["Kyle Sunderland (Perk Lab, Queen's University)"]
    self.parent.helpText = """
This is a module that organizes a workflow for brain segmentation.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Kyle Sunderland (Perk Lab, Queen's University), and was partially funded by Brigham and Women’s Hospital through NIH grant R01MH112748
"""

#
# Regular QWidget do not emit a signal when closed
# Need to subclass to emit a signal on closeEvent
#
class UndockedViewWidget(qt.QSplitter):

  closed = qt.Signal()
  def closeEvent(self, event):
    self.closed.emit()
    event.accept()

#
# NeuroSegmentWidget
#

class NeuroSegmentWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  NEURO_SEGMENT_WIDGET_LAYOUT_ID = 5612

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = NeuroSegmentLogic()

    uiWidget = slicer.util.loadUI(self.resourcePath('UI/NeuroSegment.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.ui.segmentEditorWidget.connect("masterVolumeNodeChanged (vtkMRMLVolumeNode *)", self.onMasterVolumeNodeChanged)
    self.ui.segmentEditorWidget.connect('segmentationNodeChanged(vtkMRMLSegmentationNode *)', self.onSegmentationNodeChanged)
    self.ui.undockSliceViewButton.connect('clicked()', self.toggleSliceViews)
    self.ui.infoExpandableWidget.setVisible(False)

    self.ui.reviewSubmitButton.connect('clicked()', self.onReviewSubmitClicked)

    self.segmentationNodeComboBox = self.ui.segmentEditorWidget.findChild(
      slicer.qMRMLNodeComboBox, "SegmentationNodeComboBox")
    self.segmentationNodeComboBox.nodeAddedByUser.connect(self.onNodeAddedByUser)

    self.neuroSegHistogramMethodButtonGroup = qt.QButtonGroup()
    self.neuroSegHistogramMethodButtonGroup.setExclusive(True)

    thresholdEffects = [self.ui.segmentEditorWidget.effectByName("Threshold"), self.ui.segmentEditorWidget.effectByName("LocalThreshold")]
    for thresholdEffect in thresholdEffects:
      if thresholdEffect is None:
        continue

      lowerLayout = thresholdEffect.self().histogramLowerThresholdAverageButton.parentWidget().layout()
      upperLayout = thresholdEffect.self().histogramUpperThresholdAverageButton.parentWidget().layout()

      thresholdEffect.self().histogramLowerThresholdAverageButton.hide()
      thresholdEffect.self().histogramLowerThresholdLowerButton.hide()
      thresholdEffect.self().histogramLowerThresholdMinimumButton.hide()
      thresholdEffect.self().histogramUpperThresholdAverageButton.hide()
      thresholdEffect.self().histogramUpperThresholdUpperButton.hide()
      thresholdEffect.self().histogramUpperThresholdMaximumButton.hide()

      self.histogramMinAverageThresholdButton = qt.QPushButton()
      self.histogramMinAverageThresholdButton.setText("Minimum to average")
      self.histogramMinAverageThresholdButton.setCheckable(True)
      self.histogramMinAverageThresholdButton.clicked.connect(self.updateHistogram)
      self.histogramMinAverageThresholdButton.checked = True
      lowerLayout.addWidget(self.histogramMinAverageThresholdButton)
      self.neuroSegHistogramMethodButtonGroup.addButton(self.histogramMinAverageThresholdButton)

      self.histogramAverageMaxThresholdButton = qt.QPushButton()
      self.histogramAverageMaxThresholdButton.setText("Average to maximum")
      self.histogramAverageMaxThresholdButton.setCheckable(True)
      self.histogramAverageMaxThresholdButton.clicked.connect(self.updateHistogram)
      self.histogramMinAverageThresholdButton.checked = False
      upperLayout.addWidget(self.histogramAverageMaxThresholdButton)
      self.neuroSegHistogramMethodButtonGroup.addButton(self.histogramAverageMaxThresholdButton)

    self.selectSegmentEditorParameterNode()
    uiWidget.setMRMLScene(slicer.mrmlScene)

    self.mainViewWidget3DButton = qt.QPushButton("3D")
    self.mainViewWidget3DButton.setCheckable(True)
    self.mainViewWidget3DButton.connect('clicked()', self.updateMainView)

    self.mainSliceViewName = "Main"
    self.main3DViewName = "ViewM"
    self.secondarySliceViewNames = ["Red2", "Green2", "Yellow2"]
    self.allSliceViewNames = [self.mainSliceViewName] + self. secondarySliceViewNames

    self.sliceViewWidget = None
    self.setupLayout()

    layoutManager = slicer.app.layoutManager()
    layoutManager.connect('layoutChanged(int)', self.onLayoutChanged)
    self.previousLayout = layoutManager.layout
    if self.previousLayout == NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID:
      self.previousLayout = 0

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)

    self.clickedView = None
    self.clickTimer = qt.QTimer()
    self.clickTimer.setInterval(300)
    self.clickTimer.setSingleShot(True)
    self.clickTimer.timeout.connect(self.switchMainView)
    self.clickNonResponsive = False
    self.clickNonResponseTimer = qt.QTimer()
    self.clickNonResponseTimer.setInterval(200)
    self.clickNonResponseTimer.setSingleShot(True)
    self.clickNonResponseTimer.timeout.connect(self.clickNonResponseOff)
    self.sliceViewClickObservers = []

    self.defaultSegmentationFileName = self.getPath() + "/Resources/Segmentations/DefaultSegmentation.seg.nrrd"

  def updateHistogram(self):
    thresholdEffects = [self.ui.segmentEditorWidget.effectByName("Threshold"), self.ui.segmentEditorWidget.effectByName("LocalThreshold")]
    for thresholdEffect in thresholdEffects:
      if thresholdEffect is None:
        continue
      thresholdEffect.self().histogramLowerThresholdLowerButton.setChecked(False)
      thresholdEffect.self().histogramUpperThresholdUpperButton.setChecked(False)

      if self.histogramAverageMaxThresholdButton.checked:
        thresholdEffect.self().histogramLowerThresholdAverageButton.setChecked(True)
        thresholdEffect.self().histogramLowerThresholdMinimumButton.setChecked(False)
        thresholdEffect.self().histogramUpperThresholdAverageButton.setChecked(False)
        thresholdEffect.self().histogramUpperThresholdMaximumButton.setChecked(True)
      elif self.histogramMinAverageThresholdButton.checked:
        thresholdEffect.self().histogramLowerThresholdAverageButton.setChecked(False)
        thresholdEffect.self().histogramLowerThresholdMinimumButton.setChecked(True)
        thresholdEffect.self().histogramUpperThresholdAverageButton.setChecked(True)
        thresholdEffect.self().histogramUpperThresholdMaximumButton.setChecked(False)
      thresholdEffect.self().updateMRMLFromGUI()

  def getPath(self):
    return os.path.dirname(slicer.modules.neurosegment.path)

  def enter(self):
    self.selectSegmentEditorParameterNode()
    self.updateHistogram()

    # Allow switching between effects and selected segment using keyboard shortcuts
    layoutManager = slicer.app.layoutManager()
    if layoutManager.layout == NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID:
      self.ui.segmentEditorWidget.installKeyboardShortcuts(self.sliceViewWidget)
    else:
      self.ui.segmentEditorWidget.installKeyboardShortcuts()
    self.ui.segmentEditorWidget.setupViewObservations()
    self.ui.segmentEditorWidget.updateWidgetFromMRML()

  def exit(self):
    self.ui.segmentEditorWidget.setActiveEffect(None)
    self.ui.segmentEditorWidget.removeViewObservations()
    self.ui.segmentEditorWidget.uninstallKeyboardShortcuts()

  def onSceneStartClose(self, caller, event):
    self.ui.segmentEditorWidget.setSegmentationNode(None)
    self.ui.segmentEditorWidget.removeViewObservations()

  def onSceneEndClose(self, caller, event):
    if self.parent.isEntered:
      self.selectSegmentEditorParameterNode()
      self.ui.segmentEditorWidget.updateWidgetFromMRML()

  def onSceneEndImport(self, caller, event):
    if self.parent.isEntered:
      self.selectSegmentEditorParameterNode()
      self.ui.segmentEditorWidget.updateWidgetFromMRML()

  def onNodeAddedByUser(self, node):
    if not node.AddDefaultStorageNode():
      return
    storageNode = node.GetStorageNode()
    oldFileName = storageNode.GetFileName()
    storageNode.SetFileName(self.defaultSegmentationFileName)
    storageNode.ReadData(node)
    storageNode.SetFileName(oldFileName)

  def selectSegmentEditorParameterNode(self):
    # Select parameter set node if one is found in the scene, and create one otherwise
    segmentEditorSingletonTag = "NeruoSegment.SegmentEditor"
    segmentEditorNode = slicer.mrmlScene.GetSingletonNode(segmentEditorSingletonTag, "vtkMRMLSegmentEditorNode")
    if segmentEditorNode is None:
      segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
      segmentEditorNode.SetSingletonTag(segmentEditorSingletonTag)
      segmentEditorNode = slicer.mrmlScene.AddNode(segmentEditorNode)
    if self.ui.segmentEditorWidget.mrmlSegmentEditorNode() == segmentEditorNode:
      # nothing changed
      return
    self.ui.segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)

  def setupLayout(self):
    layout = ('''
<layout type="horizontal">
 <item>
  <view class="vtkMRMLSliceNode" singletontag="'''+self.allSliceViewNames[0]+'''">
   <property name="orientation" action="default">Axial</property>
     <property name="viewlabel" action="default">M</property>
   <property name="viewcolor" action="default">#808080</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLSliceNode" singletontag="'''+self.allSliceViewNames[1]+'''">
   <property name="orientation" action="default">Axial</property>
     <property name="viewlabel" action="default">R</property>
   <property name="viewcolor" action="default">#F34A33</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLSliceNode" singletontag="'''+self.allSliceViewNames[2]+'''">
   <property name="orientation" action="default">Sagittal</property>
   <property name="viewlabel" action="default">G</property>
   <property name="viewcolor" action="default">#6EB04B</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLSliceNode" singletontag="'''+self.allSliceViewNames[3]+'''">
   <property name="orientation" action="default">Coronal</property>
   <property name="viewlabel" action="default">Y</property>
   <property name="viewcolor" action="default">#EDD54C</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLViewNode" singletontag="1">
   <property name="viewlabel" action="default">1</property>
  </view>
 </item>
 <item>
  <view class="vtkMRMLViewNode" singletontag="M">
   <property name="viewlabel" action="default">M</property>
  </view>
 </item>
</layout>''')
    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(
      NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID, layout)

  def cleanup(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(self.previousLayout)
    layoutManager.disconnect('layoutChanged(int)', self.onLayoutChanged)
    self.mainViewWidget3DButton.setParent(None)
    self.mainViewWidget3DButton = None
    self.removeObservers()

  def toggleSliceViews(self):
    if self.ui.undockSliceViewButton.checked:
      slicer.app.layoutManager().setLayout(NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID)
    else:
      slicer.app.layoutManager().setLayout(self.previousLayout)

  def updateMainView(self):
    mainSliceWidget = slicer.app.layoutManager().sliceWidget(self.mainSliceViewName)
    main3DWidget = slicer.app.layoutManager().threeDWidget(self.main3DViewName)
    if self.mainViewWidget3DButton.checked and main3DWidget is not None:
      main3DWidget.threeDController().barLayout().addWidget(self.mainViewWidget3DButton)
    else:
      mainSliceWidget.sliceController().barLayout().addWidget(self.mainViewWidget3DButton)

    # The slice view becomes unhidden if the slice intersection is modified (shift + move in other views).
    # Show/hide parent widget instead
    mainSliceWidget.parent().setVisible(not self.mainViewWidget3DButton.checked)
    if main3DWidget is not None:
      main3DWidget.setVisible(self.mainViewWidget3DButton.checked)

  def onUndockedViewClosed(self):
    widgets = []
    for sliceViewName in self.allSliceViewNames:
      widgets.append(slicer.app.layoutManager().sliceWidget(sliceViewName))
    threeDView = slicer.app.layoutManager().threeDWidget(self.main3DViewName)
    widgets.append(threeDView)

    for widget in widgets:
      if widget.window() == self.sliceViewWidget:
        widget.setParent(slicer.app.layoutManager().viewport())

    self.ui.undockSliceViewButton.setChecked(False)
    self.toggleSliceViews()

  def onLayoutChanged(self, layoutID):
    self.ui.undockSliceViewButton.setChecked(layoutID == NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID)
    if layoutID != NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID:
      self.previousLayout = layoutID
      if self.sliceViewWidget:
        self.removeSecondaryViewClickObservers()
        self.sliceViewWidget.close()
        self.ui.segmentEditorWidget.installKeyboardShortcuts()
    elif layoutID == NeuroSegmentWidget.NEURO_SEGMENT_WIDGET_LAYOUT_ID:
      self.sliceViewWidget = UndockedViewWidget(qt.Qt.Horizontal)
      self.sliceViewWidget.setAttribute(qt.Qt.WA_DeleteOnClose)
      self.sliceViewWidget.closed.connect(self.onUndockedViewClosed)
      self.ui.segmentEditorWidget.installKeyboardShortcuts(self.sliceViewWidget)

      mainViewPanel = qt.QWidget()
      mainViewLayout = qt.QHBoxLayout()
      mainViewLayout.setContentsMargins(0,0,0,0)
      mainViewPanel.setLayout(mainViewLayout)
      # The slice view becomes unhidden if the slice intersection is modified (shift + move in other views).
      # By adding it to a parent widget, we can show/hide that widget instead
      sliceViewContainer = qt.QWidget()
      sliceViewContainerLayout = qt.QHBoxLayout()
      sliceViewContainer.setLayout(sliceViewContainerLayout)
      sliceViewContainerLayout.addWidget(slicer.app.layoutManager().sliceWidget(self.mainSliceViewName))
      sliceViewContainerLayout.setContentsMargins(0,0,0,0)
      mainViewLayout.addWidget(sliceViewContainer)
      mainViewLayout.addWidget(slicer.app.layoutManager().threeDWidget(self.main3DViewName))
      self.sliceViewWidget.addWidget(mainViewPanel)

      secondaryViewPanel = qt.QWidget()
      secondaryViewLayout = qt.QVBoxLayout()
      secondaryViewLayout.setContentsMargins(0,0,0,0)
      secondaryViewPanel.setLayout(secondaryViewLayout)
      for secondaryViewName in self.secondarySliceViewNames:
        secondaryViewLayout.addWidget(slicer.app.layoutManager().sliceWidget(secondaryViewName))
      self.sliceViewWidget.addWidget(secondaryViewPanel)

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

      self.sliceViewWidget.setStretchFactor(0, 3)
      self.sliceViewWidget.setStretchFactor(1, 1)
      self.sliceViewWidget.showFullScreen() # Will not move to the other monitor with just setScreen. showFullScreen moves the window
      self.sliceViewWidget.windowHandle().setScreen(widgetScreen)
      self.sliceViewWidget.showMaximized()
      self.sliceViewWidget.show()

      self.addSecondaryViewClickObservers()

      self.updateMainView()
      masterVolumeNode = self.ui.segmentEditorWidget.masterVolumeNode()
      if masterVolumeNode is not None:
        self.onMasterVolumeNodeChanged(masterVolumeNode)

  def removeSecondaryViewClickObservers(self):
    for tag, object in self.sliceViewClickObservers:
      if object is None:
        continue
      object.RemoveObserver(tag)
    self.sliceViewClickObservers = []

  def addSecondaryViewClickObservers(self):
      self.removeSecondaryViewClickObservers()
      for viewName in self.secondarySliceViewNames:
        sliceView = slicer.app.layoutManager().sliceWidget(viewName).sliceView()
        tag = sliceView.interactor().AddObserver(vtk.vtkCommand.LeftButtonDoubleClickEvent,
                                           lambda caller, event, viewName=viewName: self.onSecondaryViewDoubleClick(viewName))
        self.sliceViewClickObservers.append((tag, sliceView.interactor()))
        tag = sliceView.interactor().AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent,
                                           lambda caller, event, viewName=viewName: self.onSecondaryViewClick(viewName))
        self.sliceViewClickObservers.append((tag, sliceView.interactor()))

  def switchMainView(self):
    layoutManager = slicer.app.layoutManager()
    sliceWidget = layoutManager.sliceWidget(self.clickedView)
    sliceNode = sliceWidget.mrmlSliceNode()
    mainSliceWidget = layoutManager.sliceWidget(self.mainSliceViewName)
    mainSliceNode = mainSliceWidget.mrmlSliceNode()
    mainSliceNode.GetSliceToRAS().DeepCopy(sliceNode.GetSliceToRAS())
    mainSliceNode.UpdateMatrices()

  def clickNonResponseOn(self):
    self.clickNonResponsive = True

  def clickNonResponseOff(self):
    self.clickNonResponsive = False

  def onSecondaryViewClick(self, viewName):
    if self.clickNonResponsive:
      return
    self.clickedView = viewName
    self.clickTimer.start()

  def onSecondaryViewDoubleClick(self, viewName):
    layoutManager = slicer.app.layoutManager()
    sliceWidget = layoutManager.sliceWidget(viewName)
    eventPositionWorld = [0,0,0,0]
    eventPosition = sliceWidget.sliceView().interactor().GetEventPosition()
    eventPositionXY = [eventPosition[0], eventPosition[1], 0, 1]
    sliceWidget.sliceLogic().GetSliceNode().GetXYToRAS().MultiplyPoint(eventPositionXY, eventPositionWorld);
    sliceNode = sliceWidget.mrmlSliceNode()
    sliceNode.JumpAllSlices(sliceNode.GetScene(),
                            eventPositionWorld[0], eventPositionWorld[1], eventPositionWorld[2],
                            slicer.vtkMRMLSliceNode.OffsetJumpSlice,
                            sliceNode.GetViewGroup(), sliceNode)
    self.clickTimer.stop()
    self.clickNonResponseOn()
    self.clickNonResponseTimer.start()

  def onMasterVolumeNodeChanged(self, volumeNode):
    self.ui.volumeThresholdWidget.setMRMLVolumeNode(volumeNode)
    self.ui.windowLevelWidget.setMRMLVolumeNode(volumeNode)
    layoutManager = slicer.app.layoutManager()
    sliceWidgetNames = layoutManager.sliceViewNames()

    volumeNodeID = ""
    if volumeNode is not None:
      volumeNodeID = volumeNode.GetID()

    for sliceWidgetName in sliceWidgetNames:
      sliceWidget = layoutManager.sliceWidget(sliceWidgetName)
      sliceWidget.mrmlSliceCompositeNode().SetBackgroundVolumeID(volumeNodeID)

  def onSegmentationNodeChanged(self, segmentationNode):
    tableNode = self.logic.getReviewTableNode(segmentationNode)
    self.ui.reviewTable.setMRMLTableNode(tableNode)

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

  def onReviewSubmitClicked(self):
    masterVolume = self.ui.segmentEditorWidget.masterVolumeNode()
    if masterVolume is None:
      logging.error("onReviewSubmitClicked: Invalid master volume!")
      return

    tableNode = self.ui.reviewTable.mrmlTableNode()
    row = tableNode.AddEmptyRow()
    table = tableNode.GetTable()

    rasToIJK = vtk.vtkMatrix4x4()
    masterVolume.GetIJKToRASMatrix(rasToIJK)
    rasToIJK.Invert()

    sliceColumn = table.GetColumnByName("Slice")
    sliceColumn.SetTuple1(row , row)

    reviewCommentsColumn = table.GetColumnByName("Review comments")
    reviewCommentsColumn.SetValue(row, self.ui.reviewTextEdit.plainText)
    self.ui.reviewTextEdit.setText("")

    table.Modified()

  def updateMRMLFromWidget(self):
    parameterNode = self.logic.getParameterNode()
    wasModifying = parameterNode.StartModify()
    parameterNode.EndModify(wasModifying)

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

  def getReviewTableNode(self, segmentationNode):
    if segmentationNode is None:
      logging.error("getReviewTableNode: Invalid segmentation node!")

    reviewTableNode = segmentationNode.GetNodeReference("ReviewTable")
    if reviewTableNode is None:
      tableName = segmentationNode.GetName() + "_ReviewTable"
      reviewTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", tableName)

      sliceArray = vtk.vtkIntArray()
      sliceArray.SetName("Slice")
      sliceArray.SetNumberOfComponents(1)
      reviewTableNode.AddColumn(sliceArray)

      reviewComments = vtk.vtkStringArray()
      reviewComments.SetName("Review comments")
      reviewTableNode.AddColumn(reviewComments)

      authorComments = vtk.vtkStringArray()
      authorComments.SetName("Author comments")
      reviewTableNode.AddColumn(authorComments)

      statusArray = vtk.vtkBitArray()
      statusArray.SetName("Status")
      reviewTableNode.AddColumn(statusArray)

      segmentationNode.SetNodeReferenceID("ReviewTable", reviewTableNode.GetID())
    return reviewTableNode

  def setOutputDirectory(self, outputDirectory):
    parameterNode = self.getParameterNode()
    outputDirectory = parameterNode.SetAttribute("OutputDirectory", outputDirectory)

  def getOutputDirectory(self):
    parameterNode = self.getParameterNode()
    outputDirectory = parameterNode.GetAttribute("OutputDirectory")
    return outputDirectory

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
    self.delayDisplay('Test passed!')
