
import os
import unittest
import string
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging

from NeuroSegmentParcellationLibs.NeuroSegmentParcellationLogic import NeuroSegmentParcellationLogic
from NeuroSegmentParcellationLibs.NeuroSegmentOutputToolWidget import NeuroSegmentOutputToolWidget
from NeuroSegmentParcellationLibs.NeuroSegmentInputMarkupsWidget import NeuroSegmentInputMarkupsWidget
from NeuroSegmentParcellationLibs.NeuroSegmentInputMarkupsFrame import NeuroSegmentInputMarkupsFrame

class NeuroSegmentParcellation(ScriptedLoadableModule, VTKObservationMixin):

  NEURO_PARCELLATION_LAYOUT_ID = 5613

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.parent.title = "Neuroparcellation"
    self.parent.categories = ["HOA 2", "Neuro Segmentation and Parcellation", "Segmentation"]
    self.parent.dependencies = ["FreeSurferMarkups"]
    self.parent.contributors = ["Kyle Sunderland (Perk Lab, Queen's University)"]
    self.parent.helpText = """
This module can be used to create a surfaced based parcellation of FreeSurfer surfaces.
""" # TODO: Add more help text + link to documentation.
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Kyle Sunderland (Perk Lab, Queen's University), and was partially funded by Brigham and Women's Hospital through NIH grant R01MH112748
"""
    if not slicer.app.commandOptions().noMainWindow:
      slicer.app.connect("startupCompleted()", self.initializeModule)

  def initializeModule(self):
    #slicer.mrmlScene.SetUndoOn()
    defaultNodes = [
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsCurveNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsLineNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsAngleNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsClosedCurveNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLLinearTransformNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLCameraNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLViewNode"),
      slicer.mrmlScene.CreateNodeByClass("vtkMRMLSliceNode"),
      ]
    for node in defaultNodes:
      node.UnRegister(None)

    for node in defaultNodes:
      node.UndoEnabledOn()
      slicer.mrmlScene.AddDefaultNode(node)
    self.setUndoOnExistingNodes()
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.setUndoOnExistingNodes)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.setUndoOnExistingNodes)

    # Setup shortcuts
    # TODO: When shortcuts are renabled in Slicer, the following section should be removed.
    def onRedo():
      slicer.mrmlScene.Redo()

    def onUndo():
      slicer.mrmlScene.Undo()

    redoShortcuts = []
    redoKeyBindings = qt.QKeySequence.keyBindings(qt.QKeySequence.Redo)
    for redoBinding in redoKeyBindings:
      redoShortcut = qt.QShortcut(slicer.util.mainWindow())
      redoShortcut.setKey(redoBinding)
      redoShortcut.connect("activated()", onRedo)
      redoShortcuts.append(redoShortcut)

    undoShortcuts = []
    undoKeyBindings = qt.QKeySequence.keyBindings(qt.QKeySequence.Undo)
    for undoBinding in undoKeyBindings:
      undoShortcut = qt.QShortcut(slicer.util.mainWindow())
      undoShortcut.setKey(undoBinding)
      undoShortcut.connect("activated()", onUndo)
      undoShortcuts.append(undoShortcut)

    self.setupLayout()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def setUndoOnExistingNodes(self, caller=None, eventId=None, node=None):
    # Camera nodes are not created using default
    cameraNodes = slicer.util.getNodesByClass("vtkMRMLCameraNode")
    for cameraNode in cameraNodes:
      cameraNode.UndoEnabledOn()

  def setupLayout(self):
    layout = ('''
<layout type="vertical">
  <item>
    <layout type="horizontal">
      <item>
        <view class="vtkMRMLViewNode" singletontag="O">
          <property name="viewlabel" action="default">O</property>
        </view>
      </item>
      <item>
        <view class="vtkMRMLViewNode" singletontag="P">
          <property name="viewlabel" action="default">P</property>
        </view>
      </item>
     <item>
        <view class="vtkMRMLViewNode" singletontag="I">
          <property name="viewlabel" action="default">I</property>
        </view>
      </item>
    </layout>
  </item>
  <item>
    <layout type="horizontal">
      <item>
        <view class="vtkMRMLSliceNode" singletontag="Red">
          <property name="orientation" action="default">Axial</property>
          <property name="viewlabel" action="default">R</property>
          <property name="viewcolor" action="default">#F34A33</property>
        </view>
      </item>
      <item>
        <view class="vtkMRMLSliceNode" singletontag="Green">
          <property name="orientation" action="default">Sagittal</property>
          <property name="viewlabel" action="default">G</property>
          <property name="viewcolor" action="default">#6EB04B</property>
        </view>
      </item>
      <item>
        <view class="vtkMRMLSliceNode" singletontag="Yellow">
          <property name="orientation" action="default">Coronal</property>
          <property name="viewlabel" action="default">Y</property>
          <property name="viewcolor" action="default">#EDD54C</property>
        </view>
      </item>
    </layout>
  </item>
</layout>''')
    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(
      NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID, layout)

class NeuroSegmentParcellationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.logic = None
    self.parameterNode = None
    self.outputModelsWidget = None
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onEndImportEvent)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/NeuroSegmentParcellation.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    self.importTypeButtonGroup = qt.QButtonGroup()
    self.importTypeButtonGroup.addButton(self.ui.markupRadioButton)
    self.importTypeButtonGroup.addButton(self.ui.overlayRadioButton)

    self.importCountButtonGroup = qt.QButtonGroup()
    self.importCountButtonGroup.addButton(self.ui.singleOverlayRadioButton)
    self.importCountButtonGroup.addButton(self.ui.multipleOverlayRadioButton)

    self.ui.intersectionGlyphComboBox.addItem("Star burst", slicer.vtkMarkupsGlyphSource2D.GlyphStarBurst)
    self.ui.intersectionGlyphComboBox.addItem("Cross", slicer.vtkMarkupsGlyphSource2D.GlyphCross)
    self.ui.intersectionGlyphComboBox.addItem("Cross dot", slicer.vtkMarkupsGlyphSource2D.GlyphCrossDot)
    self.ui.intersectionGlyphComboBox.addItem("Thick cross", slicer.vtkMarkupsGlyphSource2D.GlyphThickCross)
    self.ui.intersectionGlyphComboBox.addItem("Dash", slicer.vtkMarkupsGlyphSource2D.GlyphDash)
    self.ui.intersectionGlyphComboBox.addItem("Circle", slicer.vtkMarkupsGlyphSource2D.GlyphCircle)
    self.ui.intersectionGlyphComboBox.addItem("Vertex", slicer.vtkMarkupsGlyphSource2D.GlyphVertex)
    self.ui.intersectionGlyphComboBox.addItem("Triangle", slicer.vtkMarkupsGlyphSource2D.GlyphTriangle)
    self.ui.intersectionGlyphComboBox.addItem("Square", slicer.vtkMarkupsGlyphSource2D.GlyphSquare)
    self.ui.intersectionGlyphComboBox.addItem("Diamond", slicer.vtkMarkupsGlyphSource2D.GlyphDiamond)
    self.ui.intersectionGlyphComboBox.addItem("Arrow", slicer.vtkMarkupsGlyphSource2D.GlyphArrow)
    self.ui.intersectionGlyphComboBox.addItem("Thick arrow", slicer.vtkMarkupsGlyphSource2D.GlyphThickArrow)
    self.ui.intersectionGlyphComboBox.addItem("Hooked arrow", slicer.vtkMarkupsGlyphSource2D.GlyphHookedArrow)

    # Set scene in MRML widgets. Make sure that in Qt designer
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create a new parameterNode
    # This parameterNode stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.
    self.logic = NeuroSegmentParcellationLogic()
    self.logic.setQueryNodeFileName(self.resourcePath('Parcellation/parcellation.qry'))
    self.ui.parameterNodeSelector.addAttribute("vtkMRMLScriptedModuleNode", "ModuleName", self.moduleName)

    self.inputCurvesWidget = NeuroSegmentInputMarkupsFrame(self.logic, "vtkMRMLMarkupsCurveNode")
    self.ui.inputCurvesCollapsibleButton.layout().addWidget(self.inputCurvesWidget)

    self.inputPlanesWidget = NeuroSegmentInputMarkupsFrame(self.logic, "vtkMRMLMarkupsPlaneNode")
    self.ui.inputPlanesCollapsibleButton.layout().addWidget(self.inputPlanesWidget)

    self.setParameterNode(self.logic.getParameterNode())

    # Connections
    self.ui.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.setParameterNode)
    self.ui.parameterNodeSelector.connect('nodeAdded(vtkMRMLNode*)', self.onParameterNodeAdded)
    self.ui.loadQueryButton.connect('clicked(bool)', self.onLoadQuery)
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.exportButton.connect('clicked(bool)', self.onExportButton)
    self.ui.exportLabelButton.connect('clicked(bool)', self.onExportLabelButton)

    self.ui.markupRadioButton.connect("toggled(bool)", self.updateImportWidget)
    self.ui.overlayRadioButton.connect("toggled(bool)", self.updateImportWidget)
    self.ui.singleOverlayRadioButton.connect("toggled(bool)", self.updateImportWidget)
    self.ui.multipleOverlayRadioButton.connect("toggled(bool)", self.updateImportWidget)

    self.ui.importMarkupComboBox.connect('currentNodeChanged(vtkMRMLNode*)', self.updateImportWidget)
    self.ui.destinationMarkupComboBox.connect('currentNodeChanged(vtkMRMLNode*)', self.updateImportWidget)
    self.ui.destinationMarkupComboBox.addAttribute("vtkMRMLMarkupsNode", self.logic.NODE_TYPE_ATTRIBUTE_NAME, self.logic.ORIG_NODE_ATTRIBUTE_VALUE)
    self.ui.importOverlayComboBox.connect('currentIndexChanged(int)', self.updateImportWidget)
    self.ui.destinationModelComboBox.connect('currentNodeChanged(vtkMRMLNode*)', self.updateImportWidget)
    self.ui.destinationModelComboBox.addAttribute("vtkMRMLModelNode", self.logic.NEUROSEGMENT_OUTPUT_ATTRIBUTE_VALUE, str(True))
    self.ui.importButton.connect('clicked()', self.onImportButton)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.origModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.pialModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.inflatedModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.exportSegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)

    self.ui.curvRadioButton.connect("toggled(bool)", self.updateScalarOverlay)
    self.ui.sulcRadioButton.connect("toggled(bool)", self.updateScalarOverlay)
    self.ui.labelsRadioButton.connect("toggled(bool)", self.updateScalarOverlay)

    slicer.app.layoutManager().connect("layoutChanged(int)", self.onLayoutChanged)
    self.ui.parcellationViewLayoutButton.connect("clicked()", self.onParcellationViewLayoutButtonClicked)

    self.ui.planeIntersectionCheckBox.connect("toggled(bool)", self.onPlaneCheckBox)

    self.ui.labelOutlineCheckBox.connect("toggled(bool)", self.onLabelOutlineCheckBox)

    self.ui.origMarkupsCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.pialMarkupsCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.inflatedMarkupsCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)

    self.ui.lineViewRedCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.lineViewGreenCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.lineViewYellowCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)

    self.ui.intersectionViewRedCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.intersectionViewGreenCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.intersectionViewYellowCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)

    self.ui.intersectionGlyphComboBox.connect("currentIndexChanged(int)", self.updateMarkupDisplay)
    self.ui.curveIntersectionScaleSlider.connect("valueChanged(double)", self.updateMarkupDisplay)

    self.ui.controlPointVisibilityCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)

    self.ui.labelVisibilityCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)

    self.oldLayout = slicer.app.layoutManager().layout

    # Set path to query file
    self.ui.queryFilePathEdit.currentPath = self.logic.getQueryNodeFileName()

    # Initial GUI update
    self.updateGUIFromParameterNode()
    self.updateOutputStructures()
    self.onLayoutChanged()
    self.updateImportWidget()

  def enter(self):
    parcellationViewLayoutOpen = slicer.app.layoutManager().layout == NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID
    self.ui.parcellationViewLayoutButton.setChecked(parcellationViewLayoutOpen)
    self.logic.updateModelNodes()

  def onParcellationViewLayoutButtonClicked(self):
    if self.ui.parcellationViewLayoutButton.checked:
      self.openParcellationlayout()
    else:
      self.closeParcellationLayout()
    parcellationViewLayoutOpen = slicer.app.layoutManager().layout == NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID
    self.ui.parcellationViewLayoutButton.setChecked(parcellationViewLayoutOpen)

  def openParcellationlayout(self):
    if slicer.app.layoutManager().layout == NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID:
      return
    self.oldLayout = slicer.app.layoutManager().layout
    slicer.app.layoutManager().setLayout(NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID)
    slicer.util.getNode("ViewO").LinkedControlOn()

  def closeParcellationLayout(self):
    if slicer.app.layoutManager().layout != NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID:
      return

    if self.oldLayout == NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID:
      self.oldLayout = slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView
    slicer.app.layoutManager().setLayout(self.oldLayout)

  def onLayoutChanged(self):
    viewNode = slicer.mrmlScene.GetNodeByID("vtkMRMLViewNodeI")
    if viewNode:
      self.addInteractorObservers(viewNode)
    viewNode = slicer.mrmlScene.GetNodeByID("vtkMRMLViewNodeO")
    if viewNode:
      self.addInteractorObservers(viewNode)
    viewNode = slicer.mrmlScene.GetNodeByID("vtkMRMLViewNodeP")
    if viewNode:
      self.addInteractorObservers(viewNode)
    parcellationViewLayoutOpen = slicer.app.layoutManager().layout == NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID
    self.ui.parcellationViewLayoutButton.setChecked(parcellationViewLayoutOpen)

  def addInteractorObservers(self, viewNode):
    if viewNode is None:
      return

    layoutManager = slicer.app.layoutManager()
    view = layoutManager.threeDWidget(viewNode.GetName()).threeDView()
    interactor = view.interactor()
    if not self.hasObserver(interactor, vtk.vtkCommand.MouseMoveEvent, self.onMouseMoveIn3DView):
      self.addObserver(interactor, vtk.vtkCommand.MouseMoveEvent, self.onMouseMoveIn3DView)

    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    if not self.hasObserver(interactionNode, slicer.vtkMRMLInteractionNode.InteractionModeChangedEvent, self.onInteractionModeChanged):
      self.addObserver(interactionNode, slicer.vtkMRMLInteractionNode.InteractionModeChangedEvent, self.onInteractionModeChanged)

  def onInteractionModeChanged(self, interactionNode, event=None):
    if interactionNode is None:
      return

    selectionNode = slicer.app.applicationLogic().GetSelectionNode()
    if selectionNode is None:
      return

    currentPlaceNode = slicer.mrmlScene.GetNodeByID(selectionNode.GetActivePlaceNodeID())
    nodeType = currentPlaceNode.GetAttribute(self.logic.NODE_TYPE_ATTRIBUTE_NAME)
    if nodeType is None:
      return

    if currentPlaceNode.IsA("vtkMRMLMarkupsCurveNode") and nodeType == self.logic.ORIG_NODE_ATTRIBUTE_VALUE:
      self.logic.onMasterMarkupModified(currentPlaceNode)
    elif nodeType == self.logic.PIAL_NODE_ATTRIBUTE_VALUE or nodeType == self.logic.INFLATED_NODE_ATTRIBUTE_VALUE:
      self.logic.onDerivedControlPointsModified(currentPlaceNode)

  def onMouseMoveIn3DView(self, caller, event=None):
    if caller is None:
      return

    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    if interactionNode is None or interactionNode.GetCurrentInteractionMode() != interactionNode.Place:
      return

    selectionNode = slicer.app.applicationLogic().GetSelectionNode()

    viewNode = None
    layoutManager = slicer.app.layoutManager()
    for i in range(layoutManager.threeDViewCount):
      viewWidget = layoutManager.threeDWidget(i)
      view = viewWidget.threeDView()
      interactor = view.interactor()
      if not interactor is caller:
        continue
      viewNode = viewWidget.mrmlViewNode()

    nodeName = ""
    if viewNode:
      nodeName = viewNode.GetName()

    currentPlaceNode = slicer.mrmlScene.GetNodeByID(selectionNode.GetActivePlaceNodeID())
    nodeType = currentPlaceNode.GetAttribute(self.logic.NODE_TYPE_ATTRIBUTE_NAME)
    if nodeType is None:
      return

    origNode = None
    pialNode = None
    inflatedNode = None
    if nodeType == self.logic.ORIG_NODE_ATTRIBUTE_VALUE:
      origNode = currentPlaceNode
      pialNode = self.logic.getDerivedControlPointsNode(origNode, self.logic.PIAL_NODE_ATTRIBUTE_VALUE)
      inflatedNode = self.logic.getDerivedControlPointsNode(origNode, self.logic.INFLATED_NODE_ATTRIBUTE_VALUE)
    elif nodeType == self.logic.PIAL_NODE_ATTRIBUTE_VALUE:
      origNode = currentPlaceNode.GetNodeReference("OrigMarkup")
      pialNode = currentPlaceNode
      inflatedNode = self.logic.getDerivedControlPointsNode(origNode, self.logic.INFLATED_NODE_ATTRIBUTE_VALUE)
    elif nodeType == self.logic.INFLATED_NODE_ATTRIBUTE_VALUE:
      origNode = currentPlaceNode.GetNodeReference("OrigMarkup")
      pialNode = self.logic.getDerivedControlPointsNode(origNode, self.logic.PIAL_NODE_ATTRIBUTE_VALUE)
      inflatedNode = currentPlaceNode

    if (nodeName == "ViewI" and nodeType == self.logic.INFLATED_NODE_ATTRIBUTE_VALUE or
        nodeName == "ViewP" and nodeType == self.logic.PIAL_NODE_ATTRIBUTE_VALUE or
        nodeName == "ViewO" and nodeType == self.logic.ORIG_NODE_ATTRIBUTE_VALUE):
      return

    interactionNode.SetCurrentInteractionMode(interactionNode.Select)
    interactionNode.SetPlaceModePersistence(True)
    if nodeName == "ViewI":
      selectionNode.SetActivePlaceNodeID(inflatedNode.GetID())
      selectionNode.SetActivePlaceNodeClassName(inflatedNode.GetClassName())
    elif nodeName == "ViewP":
      selectionNode.SetActivePlaceNodeID(pialNode.GetID())
      selectionNode.SetActivePlaceNodeClassName(pialNode.GetClassName())
    else:
      selectionNode.SetActivePlaceNodeID(origNode.GetID())
      selectionNode.SetActivePlaceNodeClassName(origNode.GetClassName())
    interactionNode.SetCurrentInteractionMode(interactionNode.Place)

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.logic.removeObservers()
    self.removeObservers()
    slicer.app.layoutManager().disconnect("layoutChanged(int)", self.onLayoutChanged)

  def setParameterNode(self, inputParameterNode):
    """
    Adds observers to the selected parameter node. Observation is needed because when the
    parameter node is changed then the GUI must be updated immediately.
    """
    # Set parameter node in the parameter node selector widget
    wasBlocked = self.ui.parameterNodeSelector.blockSignals(True)
    self.ui.parameterNodeSelector.setCurrentNode(inputParameterNode)
    self.ui.parameterNodeSelector.blockSignals(wasBlocked)

    if inputParameterNode == self.parameterNode:
      # No change
      return

    self.parameterNode = inputParameterNode

    try:
      slicer.app.pauseRender()

      # Remove observers on previously selected parameter node and add an observer to the newly selected.
      # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
      # those are reflected immediately in the GUI.
      self.removeObservers(self.onParameterNodeModified)
      if self.parameterNode is not None:
        self.addObserver(self.parameterNode, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)
        self.onParameterNodeModified(self.parameterNode)

      self.inputCurvesWidget.setParameterNode(inputParameterNode)
      self.inputPlanesWidget.setParameterNode(inputParameterNode)

      # Initial GUI update
      self.logic.setParameterNode(self.parameterNode)
      self.updateGUIFromParameterNode()

    finally:
      slicer.app.resumeRender()

  def onEndImportEvent(self, caller=None, event=None):
    self.onParameterNodeModified()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onParameterNodeModified(self, caller=None, event=None, callData=None):
    if slicer.mrmlScene.IsImporting():
      return

    self.removeObservers(self.onOrigModelNodeModified)
    origModelNode = self.logic.getOrigModelNode(self.parameterNode)
    if origModelNode:
      self.addObserver(origModelNode, vtk.vtkCommand.ModifiedEvent, self.onOrigModelNodeModified)
    self.updateGUIFromParameterNode()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onOrigModelNodeModified(self, caller=None, event=None, callData=None):
    if slicer.mrmlScene.IsImporting():
      return
    self.updateImportWidget()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """
    # Disable all sections if no parameter node is selected
    self.ui.inputPlanesCollapsibleButton.enabled = self.parameterNode is not None
    self.ui.inputCurvesCollapsibleButton.enabled = self.parameterNode is not None
    self.ui.inputModelCollapsibleButton.enabled = self.parameterNode is not None
    self.ui.outputModelsCollapsibleButton.enabled = self.parameterNode is not None
    self.ui.exportSegmentationCollapsibleButton.enabled = self.parameterNode is not None
    self.ui.applyButton.enabled = self.parameterNode is not None

    if self.outputModelsWidget is not None:
      self.outputModelsWidget.deleteLater()
      self.outputModelsWidget = None

    if self.parameterNode is None:
      return

    # Display parameters
    scalarOverlay = self.logic.getScalarOverlay(self.parameterNode)
    wasBlocked = self.ui.curvRadioButton.blockSignals(True)
    self.ui.curvRadioButton.checked = scalarOverlay == "curv"
    self.ui.curvRadioButton.blockSignals(wasBlocked)

    wasBlocked = self.ui.sulcRadioButton.blockSignals(True)
    self.ui.sulcRadioButton.checked = scalarOverlay == "sulc"
    self.ui.sulcRadioButton.blockSignals(wasBlocked)

    wasBlocked = self.ui.labelsRadioButton.blockSignals(True)
    self.ui.labelsRadioButton.checked = scalarOverlay == "labels"
    self.ui.labelsRadioButton.blockSignals(wasBlocked)
    
    wasBlocked = self.ui.origMarkupsCheckBox.blockSignals(True)
    self.ui.origMarkupsCheckBox.setChecked(self.logic.getMarkupSliceViewVisibility(self.parameterNode, self.logic.ORIG_NODE_ATTRIBUTE_VALUE))
    self.ui.origMarkupsCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.pialMarkupsCheckBox.blockSignals(True)
    self.ui.pialMarkupsCheckBox.setChecked(self.logic.getMarkupSliceViewVisibility(self.parameterNode, self.logic.PIAL_NODE_ATTRIBUTE_VALUE))
    self.ui.pialMarkupsCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.inflatedMarkupsCheckBox.blockSignals(True)
    self.ui.inflatedMarkupsCheckBox.setChecked(self.logic.getMarkupSliceViewVisibility(self.parameterNode, self.logic.INFLATED_NODE_ATTRIBUTE_VALUE))
    self.ui.inflatedMarkupsCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.planeIntersectionCheckBox.blockSignals(True)
    self.ui.planeIntersectionCheckBox.setChecked(self.logic.getPlaneIntersectionVisible())
    self.ui.planeIntersectionCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.labelOutlineCheckBox.blockSignals(True)
    self.ui.labelOutlineCheckBox.setChecked(self.logic.getLabelOutlineVisible())
    self.ui.labelOutlineCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.lineViewRedCheckBox.blockSignals(True)
    self.ui.lineViewRedCheckBox.setChecked(self.logic.getRedLineVisibility())
    self.ui.lineViewRedCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.lineViewGreenCheckBox.blockSignals(True)
    self.ui.lineViewGreenCheckBox.setChecked(self.logic.getGreenLineVisibility())
    self.ui.lineViewGreenCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.lineViewYellowCheckBox.blockSignals(True)
    self.ui.lineViewYellowCheckBox.setChecked(self.logic.getYellowLineVisibility())
    self.ui.lineViewYellowCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionViewRedCheckBox.blockSignals(True)
    self.ui.intersectionViewRedCheckBox.setChecked(self.logic.getRedIntersectionVisibility())
    self.ui.intersectionViewRedCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionViewGreenCheckBox.blockSignals(True)
    self.ui.intersectionViewGreenCheckBox.setChecked(self.logic.getGreenIntersectionVisibility())
    self.ui.intersectionViewGreenCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionViewYellowCheckBox.blockSignals(True)
    self.ui.intersectionViewYellowCheckBox.setChecked(self.logic.getYellowIntersectionVisibility())
    self.ui.intersectionViewYellowCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.intersectionGlyphComboBox.blockSignals(True)
    index = self.ui.intersectionGlyphComboBox.findData(self.logic.getIntersectionGlyphType())
    self.ui.intersectionGlyphComboBox.currentIndex = index
    self.ui.intersectionGlyphComboBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.curveIntersectionScaleSlider.blockSignals(True)
    self.ui.curveIntersectionScaleSlider.value = self.logic.getIntersectionGlyphScale()
    self.ui.curveIntersectionScaleSlider.blockSignals(wasBlocked)

    wasBlocked = self.ui.controlPointVisibilityCheckBox.blockSignals(True)
    self.ui.controlPointVisibilityCheckBox.setChecked(self.logic.getControlPointVisibility())
    self.ui.controlPointVisibilityCheckBox.blockSignals(wasBlocked)

    wasBlocked = self.ui.labelVisibilityCheckBox.blockSignals(True)
    self.ui.labelVisibilityCheckBox.setChecked(self.logic.getLabelVisibility())
    self.ui.labelVisibilityCheckBox.blockSignals(wasBlocked)

    # Update each widget from parameter node
    # Need to temporarily block signals to prevent infinite recursion (MRML node update triggers
    # GUI update, which triggers MRML node update, which triggers GUI update, ...)

    wasBlocked = self.ui.origModelSelector.blockSignals(True)
    self.ui.origModelSelector.setCurrentNode(self.logic.getOrigModelNode(self.parameterNode))
    self.ui.origModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.pialModelSelector.blockSignals(True)
    self.ui.pialModelSelector.setCurrentNode(self.logic.getPialModelNode(self.parameterNode))
    self.ui.pialModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.inflatedModelSelector.blockSignals(True)
    self.ui.inflatedModelSelector.setCurrentNode(self.logic.getInflatedModelNode(self.parameterNode))
    self.ui.inflatedModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.exportSegmentationSelector.blockSignals(True)
    self.ui.exportSegmentationSelector.setCurrentNode(self.logic.getExportSegmentation())
    self.ui.exportSegmentationSelector.blockSignals(wasBlocked)

    # Update buttons states and tooltips
    if (self.logic.getNumberOfOutputModels() > 0 and self.logic.getExportSegmentation() and
      self.logic.getOrigModelNode(self.parameterNode) and self.logic.getPialModelNode(self.parameterNode)):
      self.ui.exportButton.enabled = True
    else:
      self.ui.exportButton.enabled = False

    outputModelsLayout = qt.QFormLayout()
    outputModelsLayout.verticalSpacing = 6

    self.outputModelsWidget = qt.QWidget()
    self.outputModelsWidget.setLayout(outputModelsLayout)
    self.ui.outputModelsCollapsibleButton.layout().addWidget(self.outputModelsWidget)

    for toolNode in self.logic.getToolNodes():
      outputModelNode = toolNode.GetNodeReference("BoundaryCut.OutputModel")
      outputModelName = "ERR"
      if outputModelNode:
        outputModelName = outputModelNode.GetName()
      label = qt.QLabel(outputModelName + ":")
      outputModelWidget = NeuroSegmentOutputToolWidget(self.logic)
      outputModelsLayout.addRow(label, outputModelWidget)
      outputModelWidget.setToolNode(toolNode)
      outputModelWidget.setParameterNode(self.parameterNode)

    self.updateOutputStructures()
    self.updateImportWidget()

  def createInputMarkupsWidget(self, markupNodeClass):
    markupsLayout = qt.QFormLayout()
    for inputNode in self.logic.getInputMarkupNodes():

      if inputNode.IsA(markupNodeClass):
        markupWidget = NeuroSegmentInputMarkupsWidget()
        markupWidget.setInputMarkupsNode(inputNode)
        markupsLayout.addRow(qt.QLabel(inputNode.GetName() + ":"), markupWidget)

    markupsWidget = qt.QWidget()
    markupsWidget.setLayout(markupsLayout)
    return markupsWidget

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """
    if self.parameterNode is None:
      return

    with slicer.util.NodeModify(self.parameterNode):
      self.logic.setOrigModelNode(self.parameterNode, self.ui.origModelSelector.currentNode())
      self.logic.setPialModelNode(self.parameterNode, self.ui.pialModelSelector.currentNode())
      self.logic.setInflatedModelNode(self.parameterNode, self.ui.inflatedModelSelector.currentNode())
      self.logic.setExportSegmentation(self.ui.exportSegmentationSelector.currentNode())

  def updateScalarOverlay(self):
    scalarName = "curv"
    if self.ui.curvRadioButton.isChecked():
      scalarName = "curv"
    elif self.ui.sulcRadioButton.isChecked():
      scalarName = "sulc"
    elif self.ui.labelsRadioButton.isChecked():
      scalarName = "labels"
    self.logic.setScalarOverlay(self.parameterNode, scalarName)

  def updateMarkupDisplay(self):
    """
    Update the visibility of markups in each view based on the slice visibility checkboxes
    """
    if self.parameterNode is None:
      return

    with slicer.util.NodeModify(self.parameterNode):
      self.logic.setMarkupSliceViewVisibility(self.parameterNode, self.logic.ORIG_NODE_ATTRIBUTE_VALUE, self.ui.origMarkupsCheckBox.checked)
      self.logic.setMarkupSliceViewVisibility(self.parameterNode, self.logic.PIAL_NODE_ATTRIBUTE_VALUE, self.ui.pialMarkupsCheckBox.checked)
      self.logic.setMarkupSliceViewVisibility(self.parameterNode, self.logic.INFLATED_NODE_ATTRIBUTE_VALUE, self.ui.inflatedMarkupsCheckBox.checked)

      self.logic.setIntersectionGlyphType(self.ui.intersectionGlyphComboBox.currentData)
      self.logic.setIntersectionGlyphScale(self.ui.curveIntersectionScaleSlider.value)

      self.logic.setRedLineVisibility(self.ui.lineViewRedCheckBox.checked)
      self.logic.setGreenLineVisibility(self.ui.lineViewGreenCheckBox.checked)
      self.logic.setYellowLineVisibility(self.ui.lineViewYellowCheckBox.checked)

      self.logic.setRedIntersectionVisibility(self.ui.intersectionViewRedCheckBox.checked)
      self.logic.setGreenIntersectionVisibility(self.ui.intersectionViewGreenCheckBox.checked)
      self.logic.setYellowIntersectionVisibility(self.ui.intersectionViewYellowCheckBox.checked)

      self.logic.setControlPointVisibility(self.ui.controlPointVisibilityCheckBox.checked)

      self.logic.setLabelVisibility(self.ui.labelVisibilityCheckBox.checked)

  def onApplyButton(self):
    """
    Apply all of the parcellation tools
    """
    if self.parameterNode is None:
      logging.error("onApplyButton: Invalid parameter node")
      return

    self.logic.initializePedigreeIds(self.parameterNode)

    for toolNode in self.logic.getToolNodes():
      self.logic.runDynamicModelerTool(toolNode)
    self.logic.exportOutputToSurfaceLabel(self.parameterNode)

  def onExportButton(self):
    """
    Export the mesh connecting the inner and outer surfaces when the export button is clicked
    """
    surfacesToExport = []
    checkedIndexes = self.ui.structureSelector.checkedIndexes()
    for index in checkedIndexes:
      surfacesToExport.append(self.ui.structureSelector.itemText(index.row()))

    try:
      self.logic.exportOutputToSegmentation(self.parameterNode, surfacesToExport)
    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()

  def onExportLabelButton(self):
    surfacesToExport = []
    checkedIndexes = self.ui.structureSelector.checkedIndexes()
    for index in checkedIndexes:
      surfacesToExport.append(self.ui.structureSelector.itemText(index.row()))

    self.logic.exportOutputToSurfaceLabel(self.parameterNode, surfacesToExport)

  def onParameterNodeAdded(self, parameterNode):
    """
    Called if a node is added from the combobox.
    Sets the default node parameters.
    """
    self.logic.setDefaultParameters(parameterNode)

  def onLoadQuery(self):
    """
    Load the query information from file.
    If an error occurs, change the query button icon and display an error message.
    """
    if self.parameterNode is None:
      return

    self.ui.loadQueryButton.setIcon(qt.QIcon())
    self.ui.loadQueryButton.setToolTip("")

    currentPath = self.ui.queryFilePathEdit.currentPath

    success, message = self.logic.loadQuery(currentPath)
    if not success:
      icon = self.ui.loadQueryButton.style().standardIcon(qt.QStyle.SP_MessageBoxCritical)
      self.ui.loadQueryButton.setIcon(icon)
      self.ui.loadQueryButton.setToolTip(message)

  def  updateOutputStructures(self):
    """
    Update the contents of the structure selector.
    Ensure that the same structures are selected before and after update if possible.
    """
    checkedItems = []
    checkedIndexes = self.ui.structureSelector.checkedIndexes()
    for index in checkedIndexes:
      checkedItems.append(self.ui.structureSelector.itemText(index.row()))

    self.ui.structureSelector.clear()
    for outputModel in self.logic.getOutputModelNodes():
      self.ui.structureSelector.addItem(outputModel.GetName())
      if outputModel.GetName() in checkedItems:
        row = self.ui.structureSelector.findText(outputModel.GetName())
        index = self.ui.structureSelector.model().index(row, 0)
        self.ui.structureSelector.setCheckState(index, qt.Qt.Checked)

  def updateImportWidget(self):
    """
    Update the appearance of the import/export widget.
    This enables/disables the import button depending on the validity of the input, and shows/hides/populates the
    comboboxes for the input/output nodes and overlays.
    """

    self.ui.importMarkupComboBox.setVisible(self.ui.markupRadioButton.isChecked())
    self.ui.destinationMarkupComboBox.setVisible(self.ui.markupRadioButton.isChecked())
    self.ui.importOverlayComboBox.setVisible(self.ui.overlayRadioButton.isChecked())
    self.ui.destinationModelComboBox.setVisible(self.ui.overlayRadioButton.isChecked())
    self.ui.destinationModelComboBox.setEnabled(self.ui.singleOverlayRadioButton.isChecked())

    self.ui.singleOverlayRadioButton.setVisible(self.ui.overlayRadioButton.isChecked())
    self.ui.multipleOverlayRadioButton.setVisible(self.ui.overlayRadioButton.isChecked())

    wasBlocking = self.ui.importOverlayComboBox.blockSignals(True)
    currentOverlayText = self.ui.importOverlayComboBox.currentText
    self.ui.importOverlayComboBox.clear()
    origModelNode = self.logic.getOrigModelNode(self.parameterNode)
    if origModelNode:
      overlays = self.logic.getPointScalarOverlays(origModelNode)
      for overlay in overlays:
        overlayName = overlay.GetName()
        self.ui.importOverlayComboBox.addItem(overlayName)
    currentOverlayIndex = self.ui.importOverlayComboBox.findText(currentOverlayText)
    self.ui.importOverlayComboBox.currentIndex = currentOverlayIndex
    self.ui.importOverlayComboBox.blockSignals(wasBlocking)

    importEnabled = False
    if self.ui.markupRadioButton.isChecked():
      importNode = self.ui.importMarkupComboBox.currentNode()
      destinationNode = self.ui.destinationMarkupComboBox.currentNode()
      importEnabled = not importNode is None and not destinationNode is None and importNode != destinationNode

    elif self.ui.overlayRadioButton.isChecked():
      importOverlay = self.ui.importOverlayComboBox.currentText
      destinationNode = self.ui.destinationModelComboBox.currentNode()
      importEnabled = importOverlay != ""
      if destinationNode is None and self.ui.singleOverlayRadioButton.isChecked():
        importEnabled = False

    self.ui.importButton.enabled = importEnabled

  def onImportButton(self):
    if self.ui.markupRadioButton.isChecked():
      self.importMarkupNode()
    elif self.ui.overlayRadioButton.isChecked():
      if self.ui.singleOverlayRadioButton.isChecked():
        self.importOverlay()
      else:
        self.importMultipleStructures()
    self.updateGUIFromParameterNode()

  def importMultipleStructures(self):

    origModelNode = self.logic.getOrigModelNode(self.parameterNode)
    importOverlay = self.ui.importOverlayComboBox.currentText

    originalScalarName = None
    displayNode = origModelNode.GetDisplayNode()
    if displayNode:
      originalScalarName = displayNode.GetActiveScalarName()

    # In order to populate the overlay correctly, we need to change the color table to match the label
    self.logic.setScalarOverlay(self.parameterNode, importOverlay)

    colorTableNode = origModelNode.GetDisplayNode().GetColorNode()

    layout = qt.QFormLayout()
    comboBoxes = []

    outputModelNodes = self.logic.getOutputModelNodes()
    outputModelNames = []
    outputModelIds = []
    for outputModelNode in outputModelNodes:
      outputModelNames.append(outputModelNode.GetName())
      outputModelIds.append(outputModelNode.GetID())

    for i in range(colorTableNode.GetNumberOfColors()):
      colorName = colorTableNode.GetColorName(i)
      color = [0,0,0,0]
      colorTableNode.GetColor(i, color)

      destinationComboBox = qt.QComboBox()
      destinationComboBox.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
      destinationComboBox.addItem(str(None), None)
      for i in range(len(outputModelNodes)):
        destinationComboBox.addItem(outputModelNames[i], outputModelIds[i])

      for i in range(len(color)):
        color[i] = int(255 * color[i])

      label = qt.QLabel()
      colorString = "rgb({0}, {1}, {2})".format(color[0], color[1], color[2])
      label.setStyleSheet("QLabel { background-color: " + colorString +  "}")
      label.setMinimumSize(24, 24)

      rowWidget = qt.QWidget()
      rowWidget.setLayout(qt.QHBoxLayout())
      rowWidget.layout().setContentsMargins(0,0,0,0)
      rowWidget.layout().addWidget(label)
      rowWidget.layout().addWidget(destinationComboBox)
      layout.addRow(qt.QLabel(colorName), rowWidget)
      comboBoxes.append(destinationComboBox)

    widget = qt.QWidget()
    widget.setLayout(layout)

    scrollArea = qt.QScrollArea()
    scrollArea.setWidget(widget)
    scrollArea.setWidgetResizable(True)
    scrollArea.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)

    importMultipleDialog = qt.QDialog()
    importMultipleDialog.setWindowTitle("Import multiple overlay")
    importMultipleDialog.setLayout(qt.QVBoxLayout())
    importMultipleDialog.layout().addWidget(scrollArea)
    importButton = qt.QPushButton("Import")
    qt.QObject.connect(importButton, "clicked()", importMultipleDialog, "accept()")
    importMultipleDialog.layout().addWidget(importButton)
    result = importMultipleDialog.exec()
    if result != qt.QDialog.Accepted:
      if originalScalarName:
        self.logic.setScalarOverlay(self.parameterNode, originalScalarName)
      return

    for i in range(colorTableNode.GetNumberOfColors()):
      comboBox = comboBoxes[i]

      desintationId = comboBox.currentData
      if desintationId is None:
        continue

      destinationNode = slicer.mrmlScene.GetNodeByID(desintationId)
      if destinationNode is None:
        continue

      self.logic.convertOverlayToModelNode(self.logic.getOrigModelNode(self.parameterNode), importOverlay, destinationNode, i)

      color = [0.0, 0.0, 0.0, 1.0]
      colorTableNode.GetColor(i, color)
      destinationNode.GetDisplayNode().SetColor(color[:3])
    self.logic.exportOutputToSurfaceLabel(self.parameterNode)

    # Restore the original scalar name
    if originalScalarName:
      self.logic.setScalarOverlay(self.parameterNode, originalScalarName)

  def importMarkupNode(self):
    importNode = self.ui.importMarkupComboBox.currentNode()
    destinationNode = self.ui.destinationMarkupComboBox.currentNode()
    destinationNode.CopyContent(importNode)

  def importOverlay(self):
    self.logic.initializePedigreeIds(self.parameterNode)
    importOverlay = self.ui.importOverlayComboBox.currentText
    destinationNode = self.ui.destinationModelComboBox.currentNode()
    self.logic.convertOverlayToModelNode(self.logic.getOrigModelNode(self.parameterNode), importOverlay, destinationNode)
    self.logic.exportOutputToSurfaceLabel(self.parameterNode)

  def onPlaneCheckBox(self, checked):
    if self.parameterNode is None:
      return
    self.logic.setPlaneIntersectionVisible(checked)

  def onLabelOutlineCheckBox(self, checked):
    if self.parameterNode is None:
      return
    self.logic.setLabelOutlineVisible(checked)

class NeuroSegmentParcellationTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()
    pass

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()

    self.meshParseTool1()

  def setupSphere(self, radius):

    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetRadius(radius)
    sphereSource.SetPhiResolution(75)
    sphereSource.SetThetaResolution(75)
    sphereSource.Update()

    modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    modelNode.SetAndObservePolyData(sphereSource.GetOutput())
    modelNode.CreateDefaultDisplayNodes()
    return modelNode

  def meshParseTool1(self):
    import time
    startTime = time.time()

    logic = NeuroSegmentParcellationLogic()
    parameterNode = logic.getParameterNode()

    origModelNode = self.setupSphere(50.0)
    pialModelNode = self.setupSphere(75.0)
    pialModelNode.GetDisplayNode().SetVisibility(False)

    logic.setOrigModelNode(parameterNode, origModelNode)
    logic.setPialModelNode(parameterNode, pialModelNode)

    parcellationQueryNode = slicer.vtkMRMLTextNode()
    parcellationQueryNode.SetName("ParcellationQuery")
    parcellationQueryNode.SetText("""_Planes = [ PA, PB, PC, PD ]; A = (PA & PB & PC); B = (PA & PB & PC); C = (PA & PB & PC); D = PD""")
    slicer.mrmlScene.AddNode(parcellationQueryNode)
    logic.setQueryNode(parcellationQueryNode)
    logic.parseParcellationString(parameterNode)

    planeA = slicer.util.getNode("PA")
    planeA.SetOrigin([0, 0, 0])
    planeA.SetNormal([0, 0, 1])
    planeA.GetDisplayNode().SetVisibility(False)

    planeB = slicer.util.getNode("PB")
    planeB.SetOrigin([0, 0, 0])
    planeB.SetNormal([1, 0, 0])
    planeB.GetDisplayNode().SetVisibility(False)

    planeC = slicer.util.getNode("PC")
    planeC.SetOrigin([0, 0, 0])
    planeC.SetNormal([0, 1, 0])
    planeC.GetDisplayNode().SetVisibility(False)

    i = 0
    colors = [
      [1.0, 0.0, 0.0],
      [0.0, 1.0, 0.0],
      [0.0, 0.0, 1.0],
      [1.0, 1.0, 0.0],
    ]
    for outputModelNode in logic.getOutputModelNodes():
      outputModelNode.GetDisplayNode().SetColor(colors[i])
      i+=1

    seedPositions = [
      [[-24.256452560424805, -24.25225257873535, 36.426605224609375], [23.89341163635254, -22.64985466003418, 37.68958282470703]],
      [[24.005630493164062, 29.707569122314453, 32.274898529052734],[-19.602069854736328, 18.553592681884766, 42.119205474853516]],
      [[27.62245750427246, 29.372499465942383, -29.621036529541016],[-19.98876190185547, 31.806682586669922, -32.98733901977539]],
      [],
    ]

    logic.initializePedigreeIds(parameterNode)

    i = 0
    for toolNode in logic.getToolNodes():
      seed = logic.getInputSeedNode(toolNode)
      for point in seedPositions[i]:
        seed.AddFiducial(point[0], point[1], point[2])
      seed.GetDisplayNode().SetVisibility(False)
      logic.runDynamicModelerTool(toolNode)
      i+=1

    logic.exportOutputToSurfaceLabel(parameterNode)
    logic.setScalarOverlay(parameterNode, "labels")

    testDuration = time.time() - startTime
    logging.info("Test duration: %f", testDuration)
