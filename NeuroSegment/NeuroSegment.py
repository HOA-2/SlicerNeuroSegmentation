import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
from NeuroSegmentParcellationLibs import NeuroSegmentMarkupsIntersectionDisplayManager
import json
import random

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

  NODE_ID_ROLE = qt.Qt.UserRole + 1

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = NeuroSegmentLogic()
    self._parameterNode = None

    uiWidget = slicer.util.loadUI(self.resourcePath('UI/NeuroSegment.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)
    self.ui.segmentEditorWidget.connect("masterVolumeNodeChanged (vtkMRMLVolumeNode *)", self.onMasterVolumeNodeChanged)
    self.ui.undockSliceViewButton.connect('clicked()', self.toggleSliceViews)
    self.ui.infoExpandableWidget.setVisible(False)

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

    self.ui.intersectionGlyphComboBox.addItem("Star burst", slicer.vtkMRMLMarkupsDisplayNode.StarBurst2D)
    self.ui.intersectionGlyphComboBox.addItem("Cross", slicer.vtkMRMLMarkupsDisplayNode.Cross2D)
    self.ui.intersectionGlyphComboBox.addItem("Cross dot", slicer.vtkMRMLMarkupsDisplayNode.CrossDot2D)
    self.ui.intersectionGlyphComboBox.addItem("Thick cross", slicer.vtkMRMLMarkupsDisplayNode.ThickCross2D)
    self.ui.intersectionGlyphComboBox.addItem("Dash", slicer.vtkMRMLMarkupsDisplayNode.Dash2D)
    self.ui.intersectionGlyphComboBox.addItem("Circle", slicer.vtkMRMLMarkupsDisplayNode.Circle2D)
    self.ui.intersectionGlyphComboBox.addItem("Vertex", slicer.vtkMRMLMarkupsDisplayNode.Vertex2D)
    self.ui.intersectionGlyphComboBox.addItem("Triangle", slicer.vtkMRMLMarkupsDisplayNode.Triangle2D)
    self.ui.intersectionGlyphComboBox.addItem("Square", slicer.vtkMRMLMarkupsDisplayNode.Square2D)
    self.ui.intersectionGlyphComboBox.addItem("Diamond", slicer.vtkMRMLMarkupsDisplayNode.Diamond2D)
    self.ui.intersectionGlyphComboBox.addItem("Arrow", slicer.vtkMRMLMarkupsDisplayNode.Arrow2D)
    self.ui.intersectionGlyphComboBox.addItem("Thick arrow", slicer.vtkMRMLMarkupsDisplayNode.ThickArrow2D)
    self.ui.intersectionGlyphComboBox.addItem("Hooked arrow", slicer.vtkMRMLMarkupsDisplayNode.HookedArrow2D)

    self.ui.intersectionGlyphComboBox.connect("currentIndexChanged(int)", self.updateGuideCurveDisplay)

    self.ui.curveIntersectionScaleSlider.connect("valueChanged(double)", self.updateGuideCurveDisplay)

    self.ui.addGuideCurveButton.connect('clicked()', self.onAddGuideCurveClicked)
    self.ui.removeGuideCurveButton.connect('clicked()', self.onRemoveGuideCurveClicked)

    self.ui.lineViewMainCheckBox.connect('clicked()', self.updateGuideCurveDisplay)
    self.ui.lineViewRedCheckBox.connect('clicked()', self.updateGuideCurveDisplay)
    self.ui.lineViewGreenCheckBox.connect('clicked()', self.updateGuideCurveDisplay)
    self.ui.lineViewYellowCheckBox.connect('clicked()', self.updateGuideCurveDisplay)

    self.ui.intersectionViewMainCheckBox.connect('clicked()', self.updateGuideCurveDisplay)
    self.ui.intersectionViewRedCheckBox.connect('clicked()', self.updateGuideCurveDisplay)
    self.ui.intersectionViewGreenCheckBox.connect('clicked()', self.updateGuideCurveDisplay)
    self.ui.intersectionViewYellowCheckBox.connect('clicked()', self.updateGuideCurveDisplay)

    self.ui.labelVisibilityCheckBox.connect("toggled(bool)", self.updateGuideCurveDisplay)

    self.setParameterNode(self.logic.getParameterNode())

  def onAddGuideCurveClicked(self):
    """
    TODO
    """
    curveNode = self.logic.addGuideCurve(self.ui.guideCurveImportSelector.currentNode())
    self.logic.startCurvePlacement(curveNode)
    self.ui.guideCurveImportSelector.setCurrentNode(None)

  def onRemoveGuideCurveClicked(self):
    """
    TODO
    """
    selectedGuideCurve = self.selectedGuideCurve()
    if selectedGuideCurve:
      self.logic.removeGuideCurve(selectedGuideCurve)
    self.logic.stopCurvePlacement()

  def selectedGuideCurve(self):
    if self.ui.guideCurveTableWidget.currentRow() < 0:
      return None
    nodeID = self.ui.guideCurveTableWidget.item(self.ui.guideCurveTableWidget.currentRow(), 0).data(self.NODE_ID_ROLE)
    return slicer.mrmlScene.GetNodeByID(nodeID)

  def updateGUIFromParameterNode(self):
    self.updateGuideCurveTable()

    wasBlocked = self.ui.lineViewMainCheckBox.blockSignals(True)
    self.ui.lineViewMainCheckBox.checked = self.logic.getMainLineVisibility()
    self.ui.lineViewMainCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.lineViewRedCheckBox.blockSignals(True)
    self.ui.lineViewRedCheckBox.checked = self.logic.getRedLineVisibility()
    self.ui.lineViewRedCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.lineViewGreenCheckBox.blockSignals(True)
    self.ui.lineViewGreenCheckBox.checked = self.logic.getGreenLineVisibility()
    self.ui.lineViewGreenCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.lineViewYellowCheckBox.blockSignals(True)
    self.ui.lineViewYellowCheckBox.checked = self.logic.getYellowLineVisibility()
    self.ui.lineViewYellowCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionViewMainCheckBox.blockSignals(True)
    self.ui.intersectionViewMainCheckBox.checked = self.logic.getMainIntersectionVisibility()
    self.ui.intersectionViewMainCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionViewRedCheckBox.blockSignals(True)
    self.ui.intersectionViewRedCheckBox.checked = self.logic.getRedIntersectionVisibility()
    self.ui.intersectionViewRedCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionViewGreenCheckBox.blockSignals(True)
    self.ui.intersectionViewGreenCheckBox.checked = self.logic.getGreenIntersectionVisibility()
    self.ui.intersectionViewGreenCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionViewYellowCheckBox.blockSignals(True)
    self.ui.intersectionViewYellowCheckBox.checked = self.logic.getYellowIntersectionVisibility()
    self.ui.intersectionViewYellowCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionGlyphComboBox.blockSignals(True)
    index = self.ui.intersectionGlyphComboBox.findData(self.logic.getIntersectionGlyphType())
    self.ui.intersectionGlyphComboBox.currentIndex = index
    self.ui.intersectionGlyphComboBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.curveIntersectionScaleSlider.blockSignals(True)
    self.ui.curveIntersectionScaleSlider.value = self.logic.getIntersectionGlyphScale()
    self.ui.curveIntersectionScaleSlider.blockSignals(wasBlocked)

    wasBlocked = self.ui.labelVisibilityCheckBox.blockSignals(True)
    self.ui.labelVisibilityCheckBox.setChecked(self.logic.getLabelVisibility())
    self.ui.labelVisibilityCheckBox.blockSignals(wasBlocked)

  def updateGuideCurveTable(self):
    self.ui.guideCurveTableWidget.clearContents()
    curves = self.logic.getGuideCurves()
    numberOfCurves = len(curves)
    self.ui.guideCurveTableWidget.rowCount = numberOfCurves

    for i in range(numberOfCurves):
      curveNode = curves[i]
      nodeID = curveNode.GetID()

      item = qt.QTableWidgetItem()
      item.setData(self.NODE_ID_ROLE, curveNode.GetID())
      self.ui.guideCurveTableWidget.setItem(i, 0, item)

      label = qt.QLabel(curveNode.GetName())
      self.ui.guideCurveTableWidget.setCellWidget(i, 0, label)

      placeWidget = slicer.qSlicerMarkupsPlaceWidget()
      placeWidget.findChild("QToolButton", "MoreButton").setVisible(False)
      placeWidget.findChild("ctkColorPickerButton", "ColorButton").setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)
      placeWidget.setMRMLScene(slicer.mrmlScene)
      placeWidget.setCurrentNode(curveNode)

      visibilityButton = qt.QToolButton()
      visibilityButton.setObjectName("visibilityButton")
      visibilityButton.setProperty("ID", nodeID)
      visibilityButton.setProperty("ID", nodeID)
      visibilityButton.connect('clicked(bool)', lambda visibility, id=nodeID: self.onVisibilityClicked(id))

      lockButton = qt.QToolButton()
      lockButton.setObjectName("lockButton")
      lockButton.setProperty("ID", nodeID)
      lockButton.setProperty("ID", nodeID)
      lockButton.connect('clicked(bool)', lambda visibility, id=nodeID: self.onLockClicked(id))

      markupWidget = qt.QWidget()
      markupWidget.setLayout(qt.QHBoxLayout())
      markupWidget.layout().addWidget(placeWidget)
      markupWidget.layout().addWidget(visibilityButton)
      markupWidget.layout().addWidget(lockButton)
      markupWidget.layout().setContentsMargins(0,0,0,0)

      self.ui.guideCurveTableWidget.setCellWidget(i, 1, markupWidget)

    self.updateDisplayVisibilityButtons()
    self.updateLockButtons()

  def onVisibilityClicked(self, id):
    curveNode = slicer.mrmlScene.GetNodeByID(id)
    if curveNode is None:
      return
    displayNode = curveNode.GetDisplayNode()
    if displayNode is None:
      return
    newVisibility = not displayNode.GetVisibility()
    displayNode.SetVisibility(newVisibility)
    self.updateDisplayVisibilityButtons()

  def onLockClicked(self, id):
    curveNode = slicer.mrmlScene.GetNodeByID(id)
    if curveNode is None:
      return
    curveNode.SetLocked(not curveNode.GetLocked())
    self.updateLockButtons()

  def updateDisplayVisibilityButtons(self):
    curves = self.logic.getGuideCurves()
    numberOfCurves = len(curves)
    visibilityButtons = []
    for i in range(numberOfCurves):
      cellWidget = self.ui.guideCurveTableWidget.cellWidget(i, 1)
      visibilityButtons += slicer.util.findChildren(cellWidget, name="visibilityButton")

    for visibilityButton in visibilityButtons:
      nodeID = visibilityButton.property("ID")
      node = slicer.mrmlScene.GetNodeByID(nodeID)
      if node is None:
        logging.error("updateDisplayVisibilityButtons: Could not find node with ID " + str(nodeID))
        continue

      if node.GetDisplayVisibility():
        visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
      else:
        visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerInvisible.png"))

  def updateGuideCurveDisplay(self):
    was = self.logic.getParameterNode().StartModify()
    with slicer.util.NodeModify(self.logic.getParameterNode()):
      self.logic.setMainIntersectionVisibility(self.ui.intersectionViewMainCheckBox.checked)
      self.logic.setRedIntersectionVisibility(self.ui.intersectionViewRedCheckBox.checked)
      self.logic.setGreenIntersectionVisibility(self.ui.intersectionViewGreenCheckBox.checked)
      self.logic.setYellowIntersectionVisibility(self.ui.intersectionViewYellowCheckBox.checked)

      self.logic.setMainLineVisibility(self.ui.lineViewMainCheckBox.checked)
      self.logic.setRedLineVisibility(self.ui.lineViewRedCheckBox.checked)
      self.logic.setGreenLineVisibility(self.ui.lineViewGreenCheckBox.checked)
      self.logic.setYellowLineVisibility(self.ui.lineViewYellowCheckBox.checked)

      self.logic.setIntersectionGlyphType(self.ui.intersectionGlyphComboBox.currentData)
      self.logic.setIntersectionGlyphScale(self.ui.curveIntersectionScaleSlider.value)

      self.logic.setLabelVisibility(self.ui.labelVisibilityCheckBox.checked)
    self.logic.getParameterNode().EndModify(was)

  def updateLockButtons(self):
    curves = self.logic.getGuideCurves()
    numberOfCurves = len(curves)
    lockButtons = []
    for i in range(numberOfCurves):
      cellWidget = self.ui.guideCurveTableWidget.cellWidget(i, 1)
      lockButtons += slicer.util.findChildren(cellWidget, name="lockButton")

    for lockButton in lockButtons:
      nodeID = lockButton.property("ID")
      node = slicer.mrmlScene.GetNodeByID(nodeID)
      if node is None:
        logging.error("updateLockButtons: Could not find node with ID " + str(nodeID))
        continue

      if node.GetLocked():
        lockButton.setIcon(qt.QIcon(":/Icons/Small/SlicerLock.png"))
      else:
        lockButton.setIcon(qt.QIcon(":/Icons/Small/SlicerUnlock.png"))

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
    self.setParameterNode(self.logic.getParameterNode())

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
      self.setParameterNode(self.logic.getParameterNode())

  def onSceneEndImport(self, caller, event):
    if self.parent.isEntered:
      self.selectSegmentEditorParameterNode()
      self.ui.segmentEditorWidget.updateWidgetFromMRML()
      self.setParameterNode(self.logic.getParameterNode())

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

  def setParameterNode(self, parameterNode):
    if self._parameterNode is parameterNode:
      return

    self.removeObservers(self.onParameterNodeModified)
    self.addObserver(parameterNode, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)
    self._parameterNode = parameterNode
    self.updateGUIFromParameterNode()

  def onParameterNodeModified(self, caller=None, event=None):
    self.updateGUIFromParameterNode()
    self.logic.onParameterNodeModified()

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

  GUIDE_CURVE_REFERENCE_ROLE = "GuideCurve"

  CURVE_VISIBILITY_RED_VIEW = "CurveVisibilityRedView"
  CURVE_VISIBILITY_GREEN_VIEW = "CurveVisibilityGreenView"
  CURVE_VISIBILITY_YELLOW_VIEW = "CurveVisibilityYellowView"
  CURVE_VISIBILITY_MAIN_VIEW = "CurveVisibilityMainView"

  CURVE_INTERSECTION_GLYPH_TYPE_ATTRIBUTE = "CurveIntersectionGlyphType"
  CURVE_INTERSECTION_GLYPH_SCALE_ATTRIBUTE = "CurveIntersectionGlyphScale"

  INTERSECTION_VISIBILITY_RED_VIEW = "IntersectionVisibilityRedView"
  INTERSECTION_VISIBILITY_GREEN_VIEW = "IntersectionVisibilityGreenView"
  INTERSECTION_VISIBILITY_YELLOW_VIEW = "IntersectionVisibilityYellowView"
  INTERSECTION_VISIBILITY_MAIN_VIEW = "IntersectionVisibilityMainView"

  LABEL_TEXT_VISIBILITY = "LabelTextVisibility"

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)

    #try:
    #  slicer.intersectionDisplayManager
    #except AttributeError:
    slicer.intersectionDisplayManager = NeuroSegmentMarkupsIntersectionDisplayManager.NeuroSegmentMarkupsIntersectionDisplayManager()

  def addGuideCurve(self, curveNode=None):
    """
    TODO
    """
    if curveNode is None:
      name = slicer.mrmlScene.GenerateUniqueName("GuideCurve")
      curveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", name)
      curveNode.CreateDefaultDisplayNodes()

      color = self.generateCurveColor()
      curveNode.GetDisplayNode().SetSelectedColor(color[:3])

    if self.getParameterNode().HasNodeReferenceID(self.GUIDE_CURVE_REFERENCE_ROLE, curveNode.GetID()):
      return

    self.getParameterNode().AddNodeReferenceID(self.GUIDE_CURVE_REFERENCE_ROLE, curveNode.GetID())
    curveNode.SetAttribute(slicer.intersectionDisplayManager.INTERSECTION_VISIBLE_ATTRIBUTE, str(True))

    self.onParameterNodeModified()
    return curveNode

  def generateCurveColor(self):

    colorCountStr = self.getParameterNode().GetParameter("ColorCount")
    if not colorCountStr or colorCountStr == "":
      colorCountStr = "0"
    colorCount = int(colorCountStr)+1

    genericAnatomyColorNode = slicer.mrmlScene.GetNodeByID("vtkMRMLColorTableNodeFileGenericAnatomyColors.txt")
    if genericAnatomyColorNode:
      colorCount %= genericAnatomyColorNode.GetNumberOfColors()
      currentColor = [0,0,0,0]
      genericAnatomyColorNode.GetColor(colorCount, currentColor)
    else:
      currentColor = [random.random(), random.random(), random.random(), 1.0]
      colorCount = 0

    self.getParameterNode().SetParameter("ColorCount", str(colorCount))

    return currentColor

  def removeGuideCurve(self, curveNode):
    """
    TODO
    """
    if not self.getParameterNode().HasNodeReferenceID(self.GUIDE_CURVE_REFERENCE_ROLE, curveNode.GetID()):
      return

    numberOfCurves = self.getParameterNode().GetNumberOfNodeReferences(self.GUIDE_CURVE_REFERENCE_ROLE)
    for i in range(numberOfCurves):
      if self.getParameterNode().GetNthNodeReference(self.GUIDE_CURVE_REFERENCE_ROLE, i).GetID() == curveNode.GetID():
        self.getParameterNode().RemoveNthNodeReferenceID(self.GUIDE_CURVE_REFERENCE_ROLE, i)
        slicer.mrmlScene.RemoveNode(curveNode)
        return

  def getGuideCurves(self):
    """
    TODO
    """
    numberOfCurves = self.getParameterNode().GetNumberOfNodeReferences(self.GUIDE_CURVE_REFERENCE_ROLE)
    curveNodes = []
    for i in range(numberOfCurves):
      curveNodes.append(self.getParameterNode().GetNthNodeReference(self.GUIDE_CURVE_REFERENCE_ROLE, i))
    return curveNodes

  def startCurvePlacement(self, curveNode):
    if curveNode is None:
      self.stopCurvePlacement()
      return

    slicer.modules.markups.logic().StartPlaceMode(True)
    slicer.modules.markups.logic().SetActiveListID(curveNode)

  def stopCurvePlacement(self):
    slicer.app.applicationLogic().GetInteractionNode().SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)

  def setRedIntersectionVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.INTERSECTION_VISIBILITY_RED_VIEW, str(visibility))

  def setGreenIntersectionVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.INTERSECTION_VISIBILITY_GREEN_VIEW, str(visibility))

  def setYellowIntersectionVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.INTERSECTION_VISIBILITY_YELLOW_VIEW, str(visibility))

  def getRedIntersectionVisibility(self):
    return self.getParameterNode().GetParameter(self.INTERSECTION_VISIBILITY_RED_VIEW) == str(True)

  def getGreenIntersectionVisibility(self):
    return self.getParameterNode().GetParameter(self.INTERSECTION_VISIBILITY_GREEN_VIEW) == str(True)

  def getYellowIntersectionVisibility(self):
    return self.getParameterNode().GetParameter(self.INTERSECTION_VISIBILITY_YELLOW_VIEW) == str(True)

  def setRedLineVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.CURVE_VISIBILITY_RED_VIEW, str(visibility))

  def setGreenLineVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.CURVE_VISIBILITY_GREEN_VIEW, str(visibility))

  def setYellowLineVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.CURVE_VISIBILITY_YELLOW_VIEW, str(visibility))

  def getRedLineVisibility(self):
    return self.getParameterNode().GetParameter(self.CURVE_VISIBILITY_RED_VIEW) == str(True)

  def getGreenLineVisibility(self):
    return self.getParameterNode().GetParameter(self.CURVE_VISIBILITY_GREEN_VIEW) == str(True)

  def getYellowLineVisibility(self):
    return self.getParameterNode().GetParameter(self.CURVE_VISIBILITY_YELLOW_VIEW) == str(True)

  def setMainIntersectionVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.INTERSECTION_VISIBILITY_MAIN_VIEW, str(visibility))

  def getMainIntersectionVisibility(self):
    return self.getParameterNode().GetParameter(self.INTERSECTION_VISIBILITY_MAIN_VIEW) == str(True)

  def setMainLineVisibility(self, visibility):
    self.getParameterNode().SetParameter(self.CURVE_VISIBILITY_MAIN_VIEW, str(visibility))

  def getMainLineVisibility(self):
    return self.getParameterNode().GetParameter(self.CURVE_VISIBILITY_MAIN_VIEW) == str(True)

  def getIntersectionGlyphType(self):
    glyphType = self.getParameterNode().GetParameter(self.CURVE_INTERSECTION_GLYPH_TYPE_ATTRIBUTE)
    if glyphType == "":
      return slicer.vtkMRMLMarkupsDisplayNode.Cross2D
    return slicer.vtkMRMLMarkupsDisplayNode.GetGlyphTypeFromString(glyphType)

  def setIntersectionGlyphType(self, glyphType):
    glyphTypeString = slicer.vtkMRMLMarkupsDisplayNode.GetGlyphTypeAsString(glyphType)
    self.getParameterNode().SetParameter(self.CURVE_INTERSECTION_GLYPH_TYPE_ATTRIBUTE, glyphTypeString)

  def setIntersectionGlyphScale(self, glyphScale):
    self.getParameterNode().SetParameter(self.CURVE_INTERSECTION_GLYPH_SCALE_ATTRIBUTE, str(glyphScale))

  def getIntersectionGlyphScale(self):
    glyphScaleString = self.getParameterNode().GetParameter(self.CURVE_INTERSECTION_GLYPH_SCALE_ATTRIBUTE)
    if glyphScaleString == "":
      return 0.5
    return float(glyphScaleString)

  def getLabelVisibility(self):
    return self.getParameterNode().GetParameter(self.LABEL_TEXT_VISIBILITY) == str(True)

  def setLabelVisibility(self, visibility):
     self.getParameterNode().SetParameter(self.LABEL_TEXT_VISIBILITY, str(visibility))

  def createParameterNode(self):
    parameterNode = ScriptedLoadableModuleLogic.createParameterNode(self)
    self.setDefaultParameters(parameterNode)
    return parameterNode

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if parameterNode is None:
      return

    parameterNode.SetParameter(self.CURVE_VISIBILITY_MAIN_VIEW, str(True))
    parameterNode.SetParameter(self.CURVE_VISIBILITY_RED_VIEW, str(True))
    parameterNode.SetParameter(self.CURVE_VISIBILITY_GREEN_VIEW, str(True))
    parameterNode.SetParameter(self.CURVE_VISIBILITY_YELLOW_VIEW, str(True))

    parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_MAIN_VIEW, str(False))
    parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_RED_VIEW, str(False))
    parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_GREEN_VIEW, str(True))
    parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_YELLOW_VIEW, str(False))

  def onParameterNodeModified(self, caller=None, event=None):
    """
    TODO: Add observer
    """
    intersectionViewIDs = []
    if self.getMainIntersectionVisibility():
      intersectionViewIDs.append("Main")
    if self.getRedIntersectionVisibility():
      intersectionViewIDs.append("Red")
      intersectionViewIDs.append("Red2")
    if self.getGreenIntersectionVisibility():
      intersectionViewIDs.append("Green")
      intersectionViewIDs.append("Green2")
    if self.getYellowIntersectionVisibility():
      intersectionViewIDs.append("Yellow")
      intersectionViewIDs.append("Yellow2")

    lineViewIDs = ["vtkMRMLViewNode1"]
    if self.getMainLineVisibility():
      lineViewIDs  += ["vtkMRMLSliceNodeMain"]
    if self.getRedLineVisibility():
      lineViewIDs  += ["vtkMRMLSliceNodeRed"]
      lineViewIDs  += ["vtkMRMLSliceNodeRed2"]
    if self.getGreenLineVisibility():
      lineViewIDs  += ["vtkMRMLSliceNodeGreen"]
      lineViewIDs  += ["vtkMRMLSliceNodeGreen2"]
    if self.getYellowLineVisibility():
        lineViewIDs  += ["vtkMRMLSliceNodeYellow"]
        lineViewIDs  += ["vtkMRMLSliceNodeYellow2"]

    slicer.intersectionDisplayManager.setGlyphType(self.getIntersectionGlyphType())
    slicer.intersectionDisplayManager.setGlyphScale(self.getIntersectionGlyphScale())

    labelVisibility = self.getLabelVisibility()
    curveNodes = self.getGuideCurves()
    for curveNode in curveNodes:
      curveNode.SetAttribute(slicer.intersectionDisplayManager.INTERSECTION_VIEWS_ATTRIBUTE, json.dumps(intersectionViewIDs))
      curveNode.GetDisplayNode().SetViewNodeIDs(lineViewIDs)
      curveNode.GetDisplayNode().SetPropertiesLabelVisibility(labelVisibility)

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
