
import os
import unittest
import string
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging

from NeuroSegmentParcellationLibs.NeuroSegmentParcellationLogic import NeuroSegmentParcellationLogic

class NeuroSegmentParcellation(ScriptedLoadableModule, VTKObservationMixin):

  NEURO_PARCELLATION_LAYOUT_ID = 5613

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.parent.title = "NeuroSegment Parcellation"
    self.parent.categories = ["Surface Models"]
    self.parent.dependencies = []
    self.parent.contributors = [""]
    self.parent.helpText = """"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """"""
    if not slicer.app.commandOptions().noMainWindow:
      slicer.app.connect("startupCompleted()", self.initializeModule)

  def initializeModule(self):
    #slicer.mrmlScene.SetUndoOn()
    defaultNodes = [
      slicer.vtkMRMLMarkupsFiducialNode(),
      slicer.vtkMRMLMarkupsCurveNode(),
      slicer.vtkMRMLMarkupsLineNode(),
      slicer.vtkMRMLMarkupsAngleNode(),
      slicer.vtkMRMLMarkupsClosedCurveNode(),
      slicer.vtkMRMLLinearTransformNode(),
      slicer.vtkMRMLCameraNode(),
      slicer.vtkMRMLViewNode(),
      slicer.vtkMRMLSliceNode(),
      ]

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
    self.inputPlanesWidget = None
    self.inputCurvesWidget = None
    self.outputModelsWidget = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/NeuroSegmentParcellation.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

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
    self.setParameterNode(self.logic.getParameterNode())

    # Connections
    self.ui.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.setParameterNode)
    self.ui.loadQueryButton.connect('clicked(bool)', self.onLoadQuery)
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.exportButton.connect('clicked(bool)', self.onExportButton)
    self.ui.exportLabelButton.connect('clicked(bool)', self.onExportLabelButton)

    self.ui.curveRadioButton.connect("toggled(bool)", self.updateImportWidget)
    self.ui.overlayRadioButton.connect("toggled(bool)", self.updateImportWidget)

    self.ui.importMarkupComboBox.connect('currentNodeChanged(vtkMRMLNode*)', self.updateImportWidget)
    self.ui.destinationMarkupComboBox.connect('currentNodeChanged(vtkMRMLNode*)', self.updateImportWidget)
    self.ui.destinationMarkupComboBox.addAttribute("vtkMRMLMarkupsNode", "NeuroSegmentParcellation.NodeType", "Orig")
    self.ui.importOverlayComboBox.connect('currentIndexChanged(int)', self.updateImportWidget)
    self.ui.destinationModelComboBox.connect('currentNodeChanged(vtkMRMLNode*)', self.updateImportWidget)
    self.ui.importButton.connect('clicked()', self.onImportButton)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.origModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.pialModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.inflatedModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.exportSegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.applyButton.connect('checkBoxToggled(bool)', self.updateParameterNodeFromGUI)

    self.ui.curvRadioButton.connect("toggled(bool)", self.updateScalarOverlay)
    self.ui.sulcRadioButton.connect("toggled(bool)", self.updateScalarOverlay)
    self.ui.labelsRadioButton.connect("toggled(bool)", self.updateScalarOverlay)

    self.ui.origMarkupsCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.pialMarkupsCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.inflatedMarkupsCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)
    self.ui.markupsProjectionCheckBox.connect("toggled(bool)", self.updateMarkupDisplay)

    slicer.app.layoutManager().connect("layoutChanged(int)", self.onLayoutChanged)
    self.ui.parcellationViewLayoutButton.connect("clicked()", self.onParcellationViewLayoutButtonClicked)

    self.ui.planeIntersectionCheckBox.connect("toggled(bool)", self.onPlaneCheckBox)

    self.oldLayout = slicer.app.layoutManager().layout

    # Initial GUI update
    self.updateGUIFromParameterNode()
    self.updateOutputStructures()
    self.onLayoutChanged()
    self.updateImportWidget()

  def enter(self):
    parcellationViewLayoutOpen = slicer.app.layoutManager().layout == NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID
    self.ui.parcellationViewLayoutButton.setChecked(parcellationViewLayoutOpen)

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

    currentPlaceId = selectionNode.GetActivePlaceNodeID()
    currentPlaceNode = slicer.mrmlScene.GetNodeByID(selectionNode.GetActivePlaceNodeID())
    nodeType = currentPlaceNode.GetAttribute("NeuroSegmentParcellation.NodeType")
    if nodeType is None:
      return

    if nodeType == self.logic.ORIG_NODE_ATTRIBUTE_VALUE:
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

    currentPlaceId = selectionNode.GetActivePlaceNodeID()
    currentPlaceNode = slicer.mrmlScene.GetNodeByID(selectionNode.GetActivePlaceNodeID())
    nodeType = currentPlaceNode.GetAttribute("NeuroSegmentParcellation.NodeType")
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

    try:
      slicer.app.pauseRender()

      # Remove observers on previously selected parameter node and add an observer to the newly selected.
      # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
      # those are reflected immediately in the GUI.
      if self.parameterNode is not None:
        self.removeObserver(self.parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
      if inputParameterNode is not None:
        self.addObserver(inputParameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
      self.parameterNode = inputParameterNode

      # Initial GUI update
      self.logic.setParameterNode(inputParameterNode)
      self.updateGUIFromParameterNode()

    finally:
      slicer.app.resumeRender()

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

    if self.inputPlanesWidget is not None:
      self.ui.inputPlanesCollapsibleButton.layout().removeWidget(self.inputPlanesWidget)
      self.inputPlanesWidget.setParent(None)

    if self.inputCurvesWidget is not None:
      self.ui.inputCurvesCollapsibleButton.layout().removeWidget(self.inputCurvesWidget)
      self.inputCurvesWidget.setParent(None)

    if self.outputModelsWidget is not None:
      self.ui.outputModelsCollapsibleButton.layout().removeWidget(self.outputModelsWidget)
      self.outputModelsWidget.setParent(None)

    if self.parameterNode is None:
      return

    # Update each widget from parameter node
    # Need to temporarily block signals to prevent infinite recursion (MRML node update triggers
    # GUI update, which triggers MRML node update, which triggers GUI update, ...)

    wasBlocked = self.ui.origModelSelector.blockSignals(True)
    self.ui.origModelSelector.setCurrentNode(self.logic.getOrigModelNode())
    self.ui.origModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.pialModelSelector.blockSignals(True)
    self.ui.pialModelSelector.setCurrentNode(self.logic.getPialModelNode())
    self.ui.pialModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.inflatedModelSelector.blockSignals(True)
    self.ui.inflatedModelSelector.setCurrentNode(self.logic.getInflatedModelNode())
    self.ui.inflatedModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.exportSegmentationSelector.blockSignals(True)
    self.ui.exportSegmentationSelector.setCurrentNode(self.logic.getExportSegmentation())
    self.ui.exportSegmentationSelector.blockSignals(wasBlocked)

    # Update buttons states and tooltips
    if (self.logic.getNumberOfOutputModels() > 0 and self.logic.getExportSegmentation() and
      self.logic.getOrigModelNode() and self.logic.getPialModelNode()):
      self.ui.exportButton.enabled = True
    else:
      self.ui.exportButton.enabled = False

    self.inputCurvesWidget = self.createInputMarkupsWidget("vtkMRMLMarkupsCurveNode")
    self.ui.inputCurvesCollapsibleButton.layout().addWidget(self.inputCurvesWidget)

    self.inputPlanesWidget = self.createInputMarkupsWidget("vtkMRMLMarkupsPlaneNode")
    self.ui.inputPlanesCollapsibleButton.layout().addWidget(self.inputPlanesWidget)

    continuousUpdate = True
    for toolNode in self.logic.getToolNodes():
      if not toolNode.GetContinuousUpdate():
        continuousUpdate = False
        break
    wasBlocking = self.ui.applyButton.blockSignals(True)
    self.ui.applyButton.setChecked(continuousUpdate)
    self.ui.applyButton.blockSignals(wasBlocking)

    #
    outputModelsLayout = qt.QFormLayout()
    for toolNode in self.logic.getToolNodes():
      outputModelNode = toolNode.GetNodeReference("BoundaryCut.OutputModel")
      outputModelNode .CreateDefaultDisplayNodes()
      outputModelDisplayNode = outputModelNode.GetDisplayNode()
      color = outputModelDisplayNode.GetColor()

      colorPicker = ctk.ctkColorPickerButton()
      colorPicker.setColor(qt.QColor(color[0]*255, color[1]*255, color[2]*255))
      colorPicker.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)
      colorPicker.setProperty("NodeID", outputModelNode.GetID())
      colorPicker.displayColorName = False
      colorPicker.connect('colorChanged(QColor)', lambda color, id=outputModelNode.GetID(): self.onColorChanged(color, id))

      nodeID = outputModelNode.GetID()
      visibilityButton = qt.QToolButton()
      visibilityButton.setObjectName("visibilityButton")
      visibilityButton.setProperty("ID", nodeID)
      visibilityButton.connect('clicked(bool)', lambda visibility, id=nodeID: self.onVisibilityClicked(id))

      seedNode = toolNode.GetNodeReference("BoundaryCut.InputSeed")
      seedPlaceWidget = slicer.qSlicerMarkupsPlaceWidget()
      seedPlaceWidget.setMRMLScene(slicer.mrmlScene)
      seedPlaceWidget.deleteButton().setVisible(False)
      seedPlaceWidget.findChild("QToolButton", "MoreButton").setVisible(False)
      seedPlaceWidget.findChild("ctkColorPickerButton", "ColorButton").setVisible(False)
      seedPlaceWidget.setCurrentNode(seedNode)

      computeButton = qt.QPushButton("Compute")
      computeButton.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)
      computeButton.connect('clicked(bool)', lambda visibility, id=outputModelNode.GetID(): self.onComputeClicked(id))

      outputModelLayout = qt.QHBoxLayout()
      outputModelLayout.setContentsMargins(6, 0, 0, 0)
      outputModelLayout.addWidget(colorPicker)
      outputModelLayout.addWidget(seedPlaceWidget)
      outputModelLayout.addWidget(computeButton)
      outputModelLayout.addWidget(visibilityButton)

      outputModelWidget = qt.QWidget()
      outputModelWidget.setLayout(outputModelLayout)

      label = qt.QLabel(outputModelNode.GetName())
      outputModelsLayout.addRow(label, outputModelWidget)

    self.outputModelsWidget = qt.QWidget()
    self.outputModelsWidget.setLayout(outputModelsLayout)
    self.ui.outputModelsCollapsibleButton.layout().addWidget(self.outputModelsWidget)

    self.updateOutputStructures()
    self.updateDisplayVisibilityButtons()
    self.updateLockButtons()

  def updateDisplayVisibilityButtons(self):
    logging.debug("updateDisplayVisibilityButtons: Start")
    containerWidgets = [self.outputModelsWidget, self.inputCurvesWidget, self.inputPlanesWidget]
    visibilityButtons = []
    for containerWidget in containerWidgets:
      visibilityButtons += slicer.util.findChildren(containerWidget, name="visibilityButton")

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
    logging.debug("updateDisplayVisibilityButtons: End")

  def updateLockButtons(self):
    logging.debug("updateLockButtons: Start")
    containerWidgets = [self.inputCurvesWidget, self.inputPlanesWidget]
    lockButtons = []
    for containerWidget in containerWidgets:
      lockButtons += slicer.util.findChildren(containerWidget, name="lockButton")

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
    logging.debug("updateLockButtons: End")

  def createInputMarkupsWidget(self, markupNodeClass):
    markupsLayout = qt.QFormLayout()
    for inputNode in self.logic.getInputMarkupNodes():

      if inputNode.IsA(markupNodeClass):
        placeWidget = slicer.qSlicerMarkupsPlaceWidget()
        placeWidget.findChild("QToolButton", "MoreButton").setVisible(False)
        placeWidget.findChild("ctkColorPickerButton", "ColorButton").setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)
        placeWidget.setMRMLScene(slicer.mrmlScene)
        placeWidget.setCurrentNode(inputNode)

        nodeID = inputNode.GetID()

        visibilityButton = qt.QToolButton()
        visibilityButton.setObjectName("visibilityButton")
        visibilityButton.setProperty("ID", nodeID)
        visibilityButton.connect('clicked(bool)', lambda visibility, id=nodeID: self.onVisibilityClicked(id))

        lockButton = qt.QToolButton()
        lockButton.setObjectName("lockButton")
        lockButton.setProperty("ID", nodeID)
        lockButton.connect('clicked(bool)', lambda visibility, id=inputNode.GetID(): self.onLockClicked(id))

        markupWidget = qt.QWidget()
        markupWidget.setLayout(qt.QHBoxLayout())
        markupWidget.layout().addWidget(placeWidget)
        markupWidget.layout().addWidget(visibilityButton)
        markupWidget.layout().addWidget(lockButton)
        markupsLayout.addRow(qt.QLabel(inputNode.GetName()), markupWidget)
    markupsWidget = qt.QWidget()
    markupsWidget.setLayout(markupsLayout)
    return markupsWidget

  def onColorChanged(self, color, id):
    logging.info("onColorChanged: ID = " + str(id))
    modelNode = slicer.mrmlScene.GetNodeByID(id)
    if modelNode is None:
      return
    displayNode = modelNode.GetDisplayNode()
    if displayNode is None:
      return
    newColor = [color.red()/255.0, color.green()/255.0, color.blue()/255.0]
    logging.info("onColorChanged: Color changed: " + str(newColor))
    displayNode.SetColor(newColor[0], newColor[1], newColor[2])

  def onVisibilityClicked(self, id):
    logging.info("onVisibilityClicked: ID = " + str(id))
    modelNode = slicer.mrmlScene.GetNodeByID(id)
    if modelNode is None:
      return
    displayNode = modelNode.GetDisplayNode()
    if displayNode is None:
      return
    newVisibility = not displayNode.GetVisibility()
    displayNode.SetVisibility(newVisibility)
    logging.info("onVisibilityClicked: New visibility = " + str(newVisibility))
    self.updateDisplayVisibilityButtons()

  def onLockClicked(self, id):
    markupNode = slicer.mrmlScene.GetNodeByID(id)
    if markupNode is None:
      return
    markupNode.SetLocked(not markupNode.GetLocked())
    self.updateLockButtons()

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """
    if self.parameterNode is None:
      return

    with slicer.util.NodeModify(self.parameterNode):
      self.logic.setOrigModelNode(self.ui.origModelSelector.currentNode())
      self.logic.setPialModelNode(self.ui.pialModelSelector.currentNode())
      self.logic.setInflatedModelNode(self.ui.inflatedModelSelector.currentNode())
      self.logic.setExportSegmentation(self.ui.exportSegmentationSelector.currentNode())
      self.logic.setToolNodesContinuousUpdate(self.ui.applyButton.checked)

  def updateScalarOverlay(self):
    scalarName = None
    if self.ui.curvRadioButton.isChecked():
      scalarName = "curv"
    elif self.ui.sulcRadioButton.isChecked():
      scalarName = "sulc"
    elif self.ui.labelsRadioButton.isChecked():
      scalarName = "labels"
      colorNode = self.logic.getParcellationColorNode()
    self.logic.setScalarOverlay(scalarName)

  def updateMarkupDisplay(self):
    """
    Update the visibility of markups in each view based on the slice visibility checkboxes
    """
    with slicer.util.NodeModify(self.parameterNode):
      self.logic.setMarkupSliceViewVisibility(self.parameterNode, self.logic.ORIG_NODE_ATTRIBUTE_VALUE, self.ui.origMarkupsCheckBox.isChecked())
      self.logic.setMarkupSliceViewVisibility(self.parameterNode, self.logic.PIAL_NODE_ATTRIBUTE_VALUE, self.ui.pialMarkupsCheckBox.isChecked())
      self.logic.setMarkupSliceViewVisibility(self.parameterNode, self.logic.INFLATED_NODE_ATTRIBUTE_VALUE, self.ui.inflatedMarkupsCheckBox.isChecked())
      self.logic.setMarkupProjectionEnabled(self.parameterNode, self.ui.markupsProjectionCheckBox.isChecked())

  def onApplyButton(self):
    """
    Apply all of the parcellation tools
    """
    if self.parameterNode is None:
      logging.error("onApplyButton: Invalid parameter node")
      return

    self.logic.initializePedigreeIds(self.parameterNode)

    dynamicModelerLogic = slicer.modules.dynamicmodeler.logic()
    for toolNode in self.logic.getToolNodes():
      self.logic.runDynamicModelerTool(toolNode)
    self.logic.exportOutputToSurfaceLabel(self.parameterNode)

  def onComputeClicked(self, id):
    if self.parameterNode is None:
      logging.error("onComputeClicked: Invalid parameter node")
      return

    toolNode = None
    for currentToolNode in self.logic.getToolNodes():
      toolNode = currentToolNode
      if toolNode is None:
        continue
      outputModelNode = toolNode.GetNodeReference("BoundaryCut.OutputModel")
      if outputModelNode is None:
        continue
      if outputModelNode.GetID() == id:
        break
      toolNode = None

    if toolNode is None:
      logging.error("onComputeClicked: Could not find tool node with output ID: " + id)
      return
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

  def onLoadQuery(self):
    """
    Load the query information from file.
    If an error occurs, change the query button icon and display an error message.
    """
    if self.parameterNode is None:
      return

    self.ui.loadQueryButton.setIcon(qt.QIcon())
    self.ui.loadQueryButton.setToolTip("")

    success, message = self.logic.loadQuery()
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

    self.ui.importMarkupComboBox.setVisible(False)
    self.ui.destinationMarkupComboBox.setVisible(False)
    self.ui.importOverlayComboBox.setVisible(False)
    self.ui.destinationModelComboBox.setVisible(False)

    wasBlocking = self.ui.importOverlayComboBox.blockSignals(True)
    currentOverlayText = self.ui.importOverlayComboBox.currentText
    self.ui.importOverlayComboBox.clear()
    origModelNode = self.logic.getOrigModelNode()
    if origModelNode:
      overlays = self.logic.getPointScalarOverlays(origModelNode)
      for overlay in overlays:
        self.ui.importOverlayComboBox.addItem(overlay.GetName())
    currentOverlayIndex = self.ui.importOverlayComboBox.findText(currentOverlayText)
    self.ui.importOverlayComboBox.currentIndex = currentOverlayIndex
    self.ui.importOverlayComboBox.blockSignals(wasBlocking)

    importEnabled = False
    if self.ui.curveRadioButton.isChecked():
      self.ui.importMarkupComboBox.setVisible(True)
      self.ui.destinationMarkupComboBox.setVisible(True)

      importNode = self.ui.importMarkupComboBox.currentNode()
      destinationNode = self.ui.destinationMarkupComboBox.currentNode()
      importEnabled = not importNode is None and not destinationNode is None and importNode != destinationNode

    elif self.ui.overlayRadioButton.isChecked():
      self.ui.importOverlayComboBox.setVisible(True)
      self.ui.destinationModelComboBox.setVisible(True)

      importOverlay = self.ui.importOverlayComboBox.currentText
      destinationNode = self.ui.destinationModelComboBox.currentNode()
      importEnabled = importOverlay != ""  and not destinationNode is None

    self.ui.importButton.enabled = importEnabled

  def onImportButton(self):
    if self.ui.curveRadioButton.isChecked():
      self.importMarkupNode()
    elif self.ui.overlayRadioButton.isChecked():
      self.importOverlay()

  def importMarkupNode(self):
    importNode = self.ui.importMarkupComboBox.currentNode()
    destinationNode = self.ui.destinationMarkupComboBox.currentNode()
    self.logic.copyNode(importNode, destinationNode)

  def importOverlay(self):
    self.logic.initializePedigreeIds(self.parameterNode)
    importOverlay = self.ui.importOverlayComboBox.currentText
    destinationNode = self.ui.destinationModelComboBox.currentNode()
    self.logic.convertOverlayToModelNode(self.logic.getOrigModelNode(), importOverlay, destinationNode)

  def onPlaneCheckBox(self, checked):
    if self.parameterNode is None:
      return
    self.logic.setPlaneIntersectionVisible(checked)

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

    logic.setOrigModelNode(origModelNode)
    logic.setPialModelNode(pialModelNode)

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
    logic.setScalarOverlay("labels")

    testDuration = time.time() - startTime
    logging.info("Test duration: %f", testDuration)
