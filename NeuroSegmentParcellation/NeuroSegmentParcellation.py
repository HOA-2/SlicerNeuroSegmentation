import ast
import os
import csv
import unittest
import string
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging
import ast

INPUT_MARKUPS_REFERENCE = "InputMarkups"
ORIG_MODEL_REFERENCE = "OrigModel"
PIAL_MODEL_REFERENCE = "PialModel"
INFLATED_MODEL_REFERENCE = "InflatedModel"

INPUT_QUERY_REFERENCE = "InputQuery"
OUTPUT_MODEL_REFERENCE = "OutputModel"
TOOL_NODE_REFERENCE = "ToolNode"
EXPORT_SEGMENTATION_REFERENCE = "ExportSegmentation"

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
    self._parameterNode = None
    self._inputPlanesWidget = None
    self._inputCurvesWidget = None
    self._outputModelsWidget = None

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
    self.ui.parameterNodeSelector.addAttribute("vtkMRMLScriptedModuleNode", "ModuleName", self.moduleName)
    self.setParameterNode(self.logic.getParameterNode())

    # Connections
    self.ui.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.setParameterNode)
    self.ui.loadQueryButton.connect('clicked(bool)', self.onLoadQuery)
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.exportButton.connect('clicked(bool)', self.onExportButton)
    self.ui.exportLabelButton.connect('clicked(bool)', self.onExportLabelButton)

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

    slicer.app.layoutManager().connect("layoutChanged(int)", self.onLayoutChanged)
    self.ui.parcellationViewLayoutButton.connect("clicked()", self.onParcellationViewLayoutButtonClicked)

    self.oldLayout = slicer.app.layoutManager().layout

    # Initial GUI update
    self.updateGUIFromParameterNode()
    self.updateOutputStructures()
    self.onLayoutChanged()

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

    if nodeType == "Orig":
      self.logic.onMasterMarkupModified(currentPlaceNode)
    elif nodeType == "Pial" or nodeType == "Inflated":
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
    if nodeType == "Orig":
      origNode = currentPlaceNode
      pialNode = self.logic.getDerivedControlPointsNode(origNode, "Pial")
      inflatedNode = self.logic.getDerivedControlPointsNode(origNode, "Inflated")
    elif nodeType == "Pial":
      origNode = currentPlaceNode.GetNodeReference("OrigMarkup")
      pialNode = currentPlaceNode
      inflatedNode = self.logic.getDerivedControlPointsNode(origNode, "Inflated")
    elif nodeType == "Inflated":
      origNode = currentPlaceNode.GetNodeReference("OrigMarkup")
      pialNode = self.logic.getDerivedControlPointsNode(origNode, "Pial")
      inflatedNode = currentPlaceNode

    if (nodeName == "ViewI" and nodeType == "Inflated" or
        nodeName == "ViewP" and nodeType == "Pial" or
        nodeName == "ViewO" and nodeType == "Orig"):
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

    if inputParameterNode == self._parameterNode:
      # No change
      return

    # Unobserve previusly selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    if inputParameterNode is not None:
      self.addObserver(inputParameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode

    # Initial GUI update
    self.updateGUIFromParameterNode()
    self.logic.setParameterNode(inputParameterNode)

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """
    # Disable all sections if no parameter node is selected
    self.ui.inputPlanesCollapsibleButton.enabled = self._parameterNode is not None
    self.ui.inputCurvesCollapsibleButton.enabled = self._parameterNode is not None
    self.ui.inputModelCollapsibleButton.enabled = self._parameterNode is not None
    self.ui.outputModelsCollapsibleButton.enabled = self._parameterNode is not None
    self.ui.exportSegmentationCollapsibleButton.enabled = self._parameterNode is not None

    if self._inputPlanesWidget is not None:
      self.ui.inputPlanesCollapsibleButton.layout().removeWidget(self._inputPlanesWidget)
      self._inputPlanesWidget.setParent(None)

    if self._inputCurvesWidget is not None:
      self.ui.inputCurvesCollapsibleButton.layout().removeWidget(self._inputCurvesWidget)
      self._inputCurvesWidget.setParent(None)

    if self._outputModelsWidget is not None:
      self.ui.outputModelsCollapsibleButton.layout().removeWidget(self._outputModelsWidget)
      self._outputModelsWidget.setParent(None)

    if self._parameterNode is None:
      return

    # Update each widget from parameter node
    # Need to temporarily block signals to prevent infinite recursion (MRML node update triggers
    # GUI update, which triggers MRML node update, which triggers GUI update, ...)

    wasBlocked = self.ui.origModelSelector.blockSignals(True)
    self.ui.origModelSelector.setCurrentNode(self._parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE))
    self.ui.origModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.pialModelSelector.blockSignals(True)
    self.ui.pialModelSelector.setCurrentNode(self._parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE))
    self.ui.pialModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.inflatedModelSelector.blockSignals(True)
    self.ui.inflatedModelSelector.setCurrentNode(self._parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE))
    self.ui.inflatedModelSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.exportSegmentationSelector.blockSignals(True)
    self.ui.exportSegmentationSelector.setCurrentNode(self._parameterNode.GetNodeReference(EXPORT_SEGMENTATION_REFERENCE))
    self.ui.exportSegmentationSelector.blockSignals(wasBlocked)

    # Update buttons states and tooltips
    if (self._parameterNode.GetNumberOfNodeReferences(OUTPUT_MODEL_REFERENCE) > 0 and self._parameterNode.GetNodeReference(EXPORT_SEGMENTATION_REFERENCE) and
      self._parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE) and self._parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)):
      self.ui.exportButton.enabled = True
    else:
      self.ui.exportButton.enabled = False

    self._inputCurvesWidget = self.createInputMarkupsWidget("vtkMRMLMarkupsCurveNode")
    self.ui.inputCurvesCollapsibleButton.layout().addWidget(self._inputCurvesWidget)

    self._inputPlanesWidget = self.createInputMarkupsWidget("vtkMRMLMarkupsPlaneNode")
    self.ui.inputPlanesCollapsibleButton.layout().addWidget(self._inputPlanesWidget)

    toolNode = self._parameterNode.GetNodeReference(TOOL_NODE_REFERENCE)
    if toolNode:
      wasBlocking = self.ui.applyButton.blockSignals(True)
      self.ui.applyButton.setChecked(toolNode.GetContinuousUpdate())
      self.ui.applyButton.blockSignals(wasBlocking)

    #
    outputModelsLayout = qt.QFormLayout()
    for i in range(self._parameterNode.GetNumberOfNodeReferences(OUTPUT_MODEL_REFERENCE)):
      outputModelNode = self._parameterNode.GetNthNodeReference(OUTPUT_MODEL_REFERENCE, i)
      outputModelNode .CreateDefaultDisplayNodes()
      outputModelDisplayNode = outputModelNode.GetDisplayNode()
      color = outputModelDisplayNode.GetColor()

      colorPicker = ctk.ctkColorPickerButton()
      colorPicker.setColor(qt.QColor(color[0]*255, color[1]*255, color[2]*255))
      colorPicker.setProperty("NodeID", outputModelNode.GetID())
      colorPicker.displayColorName = False
      colorPicker.connect('colorChanged(QColor)', lambda color, id=outputModelNode.GetID(): self.onColorChanged(color, id))

      visibilityButton = qt.QToolButton()
      if outputModelDisplayNode.GetVisibility():
        visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
      else:
        visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerInvisible.png"))
      visibilityButton.connect('clicked(bool)', lambda visibility, id=outputModelNode.GetID(): self.onVisibilityClicked(id))

      outputModelLayout = qt.QHBoxLayout()
      outputModelLayout.setContentsMargins(6, 0, 0, 0)
      outputModelLayout.addWidget(colorPicker)
      outputModelLayout.addWidget(visibilityButton)

      outputModelWidget = qt.QWidget()
      outputModelWidget.setLayout(outputModelLayout)

      label = qt.QLabel(outputModelNode.GetName())
      outputModelsLayout.addRow(label, outputModelWidget)

    self._outputModelsWidget = qt.QWidget()
    self._outputModelsWidget.setLayout(outputModelsLayout)
    self.ui.outputModelsCollapsibleButton.layout().addWidget(self._outputModelsWidget)

    self.updateOutputStructures()

  def createInputMarkupsWidget(self, markupNodeClass):
    markupsLayout = qt.QFormLayout()
    for i in range(self._parameterNode.GetNumberOfNodeReferences(INPUT_MARKUPS_REFERENCE)):
      inputNode = self._parameterNode.GetNthNodeReference(INPUT_MARKUPS_REFERENCE, i)
      if inputNode.IsA(markupNodeClass):
        placeWidget = slicer.qSlicerMarkupsPlaceWidget()
        placeWidget.findChild("QToolButton", "MoreButton").setVisible(False)
        placeWidget.setMRMLScene(slicer.mrmlScene)
        placeWidget.setCurrentNode(inputNode)

        visibilityButton = qt.QToolButton()
        inputNode.CreateDefaultDisplayNodes()
        displayNode = inputNode.GetDisplayNode()
        if displayNode.GetVisibility():
          visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
        else:
          visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerInvisible.png"))
        visibilityButton.connect('clicked(bool)', lambda visibility, id=inputNode.GetID(): self.onVisibilityClicked(id))

        lockButton = qt.QToolButton()
        inputNode.CreateDefaultDisplayNodes()
        if inputNode.GetLocked():
          lockButton.setIcon(qt.QIcon(":/Icons/Small/SlicerLock.png"))
        else:
          lockButton.setIcon(qt.QIcon(":/Icons/Small/SlicerUnlock.png"))
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
    modelNode = slicer.mrmlScene.GetNodeByID(id)
    if modelNode is None:
      return
    displayNode = modelNode.GetDisplayNode()
    if displayNode is None:
      return
    displayNode.SetColor(color.red()/255.0, color.green()/255.0, color.blue()/255.0)

  def onVisibilityClicked(self, id):
    modelNode = slicer.mrmlScene.GetNodeByID(id)
    if modelNode is None:
      return
    displayNode = modelNode.GetDisplayNode()
    if displayNode is None:
      return
    displayNode.SetVisibility(not displayNode.GetVisibility())
    self.updateGUIFromParameterNode()

  def onLockClicked(self, id):
    markupNode = slicer.mrmlScene.GetNodeByID(id)
    if markupNode is None:
      return
    markupNode.SetLocked(not markupNode.GetLocked())
    self.updateGUIFromParameterNode()

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """
    if self._parameterNode is None:
      return

    wasModifying = self._parameterNode.StartModify()
    self._parameterNode.SetNodeReferenceID(ORIG_MODEL_REFERENCE, self.ui.origModelSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(PIAL_MODEL_REFERENCE, self.ui.pialModelSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(INFLATED_MODEL_REFERENCE, self.ui.inflatedModelSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(EXPORT_SEGMENTATION_REFERENCE, self.ui.exportSegmentationSelector.currentNodeID)
    numberOfToolNodes = self._parameterNode.GetNumberOfNodeReferences(TOOL_NODE_REFERENCE)
    for i in range(numberOfToolNodes):
      toolNode = self._parameterNode.GetNthNodeReference(TOOL_NODE_REFERENCE, i)
      toolNode.SetContinuousUpdate(self.ui.applyButton.checked)
    self._parameterNode.EndModify(wasModifying)

  def updateScalarOverlay(self):
    scalarName = None
    colorNode = None
    attributeType = 0
    if self.ui.curvRadioButton.isChecked():
      scalarName = "curv"
      attributeType = vtk.vtkDataObject.POINT
      colorNode = slicer.util.getNode("RedGreen")
    elif self.ui.sulcRadioButton.isChecked():
      scalarName = "sulc"
      attributeType = vtk.vtkDataObject.POINT
      colorNode = slicer.util.getNode("RedGreen")
    elif self.ui.labelsRadioButton.isChecked():
      scalarName = "labels"
      attributeType = vtk.vtkDataObject.CELL
      colorNode = self.logic.getParcellationColorNode()
    if scalarName is None:
      return

    modelNodes = [
      self._parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE),
      self._parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE),
      self._parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE),
      ]
    for modelNode in modelNodes:
      if modelNode is None:
        continue
      displayNode = modelNode.GetDisplayNode()
      if displayNode is None:
        continue
      displayNode.SetActiveScalar(scalarName, attributeType)
      if colorNode:
        displayNode.SetAndObserveColorNodeID(colorNode.GetID())

  def onApplyButton(self):
    """
    Apply all of the parcellation tools
    """
    if self._parameterNode is None:
      logging.error("Invalid parameter node")
      return

    self.logic.initializePedigreeIds(self._parameterNode)

    numberOfToolNodes = self._parameterNode.GetNumberOfNodeReferences(TOOL_NODE_REFERENCE)
    dynamicModelerLogic = slicer.modules.dynamicmodeler.logic()
    for i in range(numberOfToolNodes):
      toolNode = self._parameterNode.GetNthNodeReference(TOOL_NODE_REFERENCE, i)
      numberOfInputMarkups = toolNode.GetNumberOfNodeReferences("BoundaryCut.InputBorder")
      toolHasAllInputs = True
      for inputNodeIndex in range(numberOfInputMarkups):
        inputNode = toolNode.GetNthNodeReference("BoundaryCut.InputBorder", inputNodeIndex)
        if inputNode is None:
          continue
        if inputNode.GetNumberOfControlPoints() == 0:
          toolHasAllInputs = False
          break
      if toolHasAllInputs:
        dynamicModelerLogic.RunDynamicModelerTool(toolNode)
      else:
        outputModel = toolNode.GetNodeReference("BoundaryCut.OutputModel")
        if outputModel and outputModel.GetPolyData():
          outputModel.GetPolyData().Initialize()

    self.logic.exportOutputToSurfaceLabel(self._parameterNode)

  def onExportButton(self):
    """
    Export the mesh connecting the inner and outer surfaces when the export button is clicked
    """
    surfacesToExport = []
    checkedIndexes = self.ui.structureSelector.checkedIndexes()
    for index in checkedIndexes:
      surfacesToExport.append(self.ui.structureSelector.itemText(index.row()))

    try:
      self.logic.exportOutputToSegmentation(self._parameterNode, surfacesToExport)
    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()

  def onExportLabelButton(self):
    surfacesToExport = []
    checkedIndexes = self.ui.structureSelector.checkedIndexes()
    for index in checkedIndexes:
      surfacesToExport.append(self.ui.structureSelector.itemText(index.row()))

    self.logic.exportOutputToSurfaceLabel(self._parameterNode, surfacesToExport)

  def onLoadQuery(self):
    """
    Setup nodes
    """
    if self._parameterNode is None:
      return

    self.ui.loadQueryButton.setIcon(qt.QIcon())
    self.ui.loadQueryButton.setToolTip("")

    parcellationQueryNode = self._parameterNode.GetNodeReference(INPUT_QUERY_REFERENCE)
    if parcellationQueryNode is None:
      parcellationQueryNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode", "ParcellationQuery")
      self._parameterNode.SetNodeReferenceID(INPUT_QUERY_REFERENCE, parcellationQueryNode.GetID())

    storageNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextStorageNode")
    storageNode.SetFileName(self.resourcePath('Parcellation/parcellation.qry'))
    storageNode.ReadData(parcellationQueryNode)
    slicer.mrmlScene.RemoveNode(storageNode)

    self._parameterNode.RemoveNodeReferenceIDs(INPUT_MARKUPS_REFERENCE)
    self._parameterNode.RemoveNodeReferenceIDs(OUTPUT_MODEL_REFERENCE)
    success, message = self.logic.parseParcellationString(self._parameterNode)
    if not success:
      icon = self.ui.loadQueryButton.style().standardIcon(qt.QStyle.SP_MessageBoxCritical)
      self.ui.loadQueryButton.setIcon(icon)
      self.ui.loadQueryButton.setToolTip(message)
    self.updateOutputStructures()

  def  updateOutputStructures(self):
    """
    """
    checkedItems = []
    checkedIndexes = self.ui.structureSelector.checkedIndexes()
    for index in checkedIndexes:
      checkedItems.append(self.ui.structureSelector.itemText(index.row()))

    self.ui.structureSelector.clear()
    numOutputModels = self._parameterNode.GetNumberOfNodeReferences(OUTPUT_MODEL_REFERENCE)
    for i in range(numOutputModels):
      outputModel = self._parameterNode.GetNthNodeReference(OUTPUT_MODEL_REFERENCE, i)
      self.ui.structureSelector.addItem(outputModel.GetName())
      if outputModel.GetName() in checkedItems:
        row = self.ui.structureSelector.findText(outputModel.GetName())
        index = self.ui.structureSelector.model().index(row, 0)
        self.ui.structureSelector.setCheckState(index, qt.Qt.Checked)

class NeuroSegmentParcellationLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):
  """Perform filtering
  """
  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.isSingletonParameterNode = False

    self.origPointLocator = vtk.vtkPointLocator()
    self.pialPointLocator = vtk.vtkPointLocator()
    self.inflatedPointLocator = vtk.vtkPointLocator()
    self.inputMarkupObservers = []
    self.parameterNode = None
    self.updatingFromMasterMarkup = False
    self.updatingFromDerivedMarkup = False

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.updateParameterNodeObservers)
    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)
    self.updateParameterNodeObservers()

  def setParameterNode(self, parameterNode):
    """Set the current parameter node and initialize all unset parameters to their default values"""
    if self.parameterNode==parameterNode:
      return
    self.parameterNode = parameterNode
    self.onParameterNodeModified(parameterNode)

  def getParameterNode(self):
    """Returns the current parameter node and creates one if it doesn't exist yet"""
    if not self.parameterNode:
      self.setParameterNode(ScriptedLoadableModuleLogic.getParameterNode(self) )
    return self.parameterNode

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def updateParameterNodeObservers(self, caller=None, eventId=None, callData=None):
    scriptedModuleNodes = slicer.util.getNodesByClass("vtkMRMLScriptedModuleNode")
    for node in scriptedModuleNodes:
      if node.GetAttribute("ModuleName") == self.moduleName:
        if not self.hasObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified):
          self.addObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)
        self.onParameterNodeModified(node)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, eventId, node):
    if node is None:
      return
    if not node.IsA("vtkMRMLScriptedModuleNode"):
      return
    if not node.GetAttribute("ModuleName") == self.moduleName:
      return
    if not self.hasObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified):
      self.addObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)

  def onParameterNodeModified(self, parameterNode, eventId=None):
    if parameterNode is None:
      return

    self.updateInputMarkupObservers(parameterNode)
    self.updateAllModelViews(parameterNode)
    self.updatePointLocators(parameterNode)

    origModelNode = parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)
    numberOfToolNodes = parameterNode.GetNumberOfNodeReferences(TOOL_NODE_REFERENCE)
    for i in range(numberOfToolNodes):
      toolNode = parameterNode.GetNthNodeReference(TOOL_NODE_REFERENCE, i)
      if origModelNode is None:
        toolNode.RemoveNodeReferenceIDs("BoundaryCut.InputModel")
      elif toolNode.GetNodeReference("BoundaryCut.InputModel") != origModelNode:
        toolNode.SetNodeReferenceID("BoundaryCut.InputModel", origModelNode.GetID())

    numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfMarkupNodes):
      inputCurveNode = parameterNode.GetNthNodeReference(INPUT_MARKUPS_REFERENCE, i)
      if inputCurveNode.IsA("vtkMRMLMarkupsCurveNode"):
        inputCurveNode.SetAndObserveShortestDistanceSurfaceNode(origModelNode)

        sulcArray = None
        curvArray = None
        if origModelNode and origModelNode.GetPolyData() and origModelNode.GetPolyData().GetPointData():
          sulcArray = origModelNode.GetPolyData().GetPointData().GetArray("sulc")
          curvArray = origModelNode.GetPolyData().GetPointData().GetArray("curv")

        distanceWeightingFunction = inputCurveNode.GetAttribute("DistanceWeightingFunction")
        if distanceWeightingFunction and distanceWeightingFunction != "" and sulcArray and curvArray:
          sulcRange = sulcArray.GetRange()
          curvRange = curvArray.GetRange()
          distanceWeightingFunction = distanceWeightingFunction.replace("sulcMin", str(sulcRange[0]))
          distanceWeightingFunction = distanceWeightingFunction.replace("curvMin", str(curvRange[0]))
          distanceWeightingFunction = distanceWeightingFunction.replace("sulcMax", str(sulcRange[1]))
          distanceWeightingFunction = distanceWeightingFunction.replace("curvMax", str(curvRange[1]))
          inverseSquaredType = inputCurveNode.GetSurfaceCostFunctionTypeFromString('inverseSquared')
          inputCurveNode.SetSurfaceCostFunctionType(inverseSquaredType)
          inputCurveNode.SetSurfaceDistanceWeightingFunction(distanceWeightingFunction)
        else:
          distanceType = inputCurveNode.GetSurfaceCostFunctionTypeFromString('distance')
          inputCurveNode.SetSurfaceCostFunctionType(distanceType)

  def updateAllModelViews(self, parameterNode):
    if parameterNode is None:
      return

    sliceViewIDs = ["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow"]

    self.updateModelViews(parameterNode, ORIG_MODEL_REFERENCE, "vtkMRMLViewNodeO")
    self.updateModelViews(parameterNode, PIAL_MODEL_REFERENCE, "vtkMRMLViewNodeP")
    self.updateModelViews(parameterNode, INFLATED_MODEL_REFERENCE, "vtkMRMLViewNodeI")
    self.updateModelViews(parameterNode, OUTPUT_MODEL_REFERENCE, "vtkMRMLViewNodeO")

  def updateModelViews(self, parameterNode, modelReference, viewID):
    if parameterNode is None:
      return

    viewIDs = ["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", viewID]
    numberOfModels = parameterNode.GetNumberOfNodeReferences(modelReference)
    for i in range(numberOfModels):
      modelNode = parameterNode.GetNthNodeReference(modelReference, i)
      if modelNode is None:
        continue
      modelNode.GetDisplayNode().SetViewNodeIDs(viewIDs)

  def updatePointLocators(self, parameterNode):
    if parameterNode is None:
      return

    origModelNode = parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)
    if origModelNode is not None and self.origPointLocator.GetDataSet() != origModelNode.GetPolyData():
        self.origPointLocator.SetDataSet(origModelNode.GetPolyData())
        self.origPointLocator.BuildLocator()

    pialModelNode = parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
    if pialModelNode is not None and self.pialPointLocator.GetDataSet() != pialModelNode.GetPolyData():
        self.pialPointLocator.SetDataSet(pialModelNode.GetPolyData())
        self.pialPointLocator.BuildLocator()

    inflatedModelNode = parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE)
    if inflatedModelNode is not None and self.inflatedPointLocator.GetDataSet() != inflatedModelNode.GetPolyData():
        self.inflatedPointLocator.SetDataSet(inflatedModelNode.GetPolyData())
        self.inflatedPointLocator.BuildLocator()

  def removeObservers(self):
    VTKObservationMixin.removeObservers(self)
    self.removeInputMarkupObservers()

  def removeInputMarkupObservers(self):
    for obj, tag in self.inputMarkupObservers:
      obj.RemoveObserver(tag)
    self.inputMarkupObservers = []

  def updateInputMarkupObservers(self, parameterNode):
    self.removeInputMarkupObservers()
    if parameterNode is None:
      return

    numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfMarkupNodes):
      inputMarkupNode = parameterNode.GetNthNodeReference(INPUT_MARKUPS_REFERENCE, i)
      if not inputMarkupNode.IsA("vtkMRMLMarkupsCurveNode"):
        continue
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      inputMarkupNode.GetDisplayNode().SetViewNodeIDs(["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", "vtkMRMLViewNodeO"])
      inputMarkupNode.SetAttribute("NeuroSegmentParcellation.NodeType", "Orig")

      pialControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, "Pial")
      if pialControlPoints:
        tag = pialControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((pialControlPoints, tag))
        tag = pialControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((pialControlPoints, tag))
        pialControlPoints.GetDisplayNode().SetViewNodeIDs(["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", "vtkMRMLViewNodeP"])

      inflatedControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, "Inflated")
      if inflatedControlPoints:
        tag = inflatedControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((inflatedControlPoints, tag))
        tag = inflatedControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((inflatedControlPoints, tag))
        inflatedControlPoints.GetDisplayNode().SetViewNodeIDs(["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", "vtkMRMLViewNodeI"])

      pialCurveNode = self.getDerivedCurveNode(inputMarkupNode, "Pial")
      if pialCurveNode:
        #tag = pialCurveNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onDerivedCurvePointAdded)
        #self.inputMarkupObservers.append((pialCurveNode, tag))
        pialCurveNode.GetDisplayNode().SetViewNodeIDs(["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", "vtkMRMLViewNodeP"])

      inflatedCurveNode = self.getDerivedCurveNode(inputMarkupNode, "Inflated")
      if inflatedCurveNode:
        #tag = inflatedCurveNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onDerivedCurvePointAdded)
        #self.inputMarkupObservers.append((inflatedCurveNode, tag))
        inflatedCurveNode.GetDisplayNode().SetViewNodeIDs(["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", "vtkMRMLViewNodeI"])

  def onMasterMarkupModified(self, inputMarkupNode, eventId=None, node=None):
    if self.updatingFromMasterMarkup or self.parameterNode is None:
      return

    origModel = self.parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
    if origModel is None:
      return

    curvePoints = inputMarkupNode.GetCurve().GetPoints()
    if self.origPointLocator.GetDataSet() is None or curvePoints is None:
      return

    self.updatingFromMasterMarkup = True

    pointIds = []
    for i in range(curvePoints.GetNumberOfPoints()):
      origPoint = list(curvePoints.GetPoint(i))
      origModel.TransformPointFromWorld(origPoint, origPoint)
      pointIds.append(self.origPointLocator.FindClosestPoint(origPoint))

    pialMarkup = self.getDerivedCurveNode(inputMarkupNode, "Pial")
    if pialMarkup:
      pialModel = self.parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
      if pialModel and pialModel.GetPolyData() and pialModel.GetPolyData().GetPoints():
        wasModifying = pialMarkup.StartModify()
        pialPoints = vtk.vtkPoints()
        pointIndex = 0
        pialPoints.SetNumberOfPoints(len(pointIds))
        for pointId in pointIds:
          pialPoint = list(pialModel.GetPolyData().GetPoints().GetPoint(pointId))
          pialModel.TransformPointToWorld(pialPoint, pialPoint)
          pialPoints.SetPoint(pointIndex, pialPoint)
          pointIndex += 1
        pialMarkup.SetControlPointPositionsWorld(pialPoints)
        for pointIndex in range(len(pointIds)):
          pialMarkup.SetNthControlPointVisibility(pointIndex, False)
        pialMarkup.EndModify(wasModifying)

    inflatedMarkup = self.getDerivedCurveNode(inputMarkupNode, "Inflated")
    if inflatedMarkup:
      inflatedModel = self.parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE)
      if inflatedModel and inflatedModel.GetPolyData() and inflatedModel.GetPolyData().GetPoints():
        wasModifying = inflatedMarkup.StartModify()
        inflatedPoints = vtk.vtkPoints()
        inflatedPoints.SetNumberOfPoints(len(pointIds))
        pointIndex = 0
        for pointId in pointIds:
          inflatedPoint = list(inflatedModel.GetPolyData().GetPoints().GetPoint(pointId))
          inflatedModel.TransformPointToWorld(inflatedPoint, inflatedPoint)
          inflatedPoints.SetPoint(pointIndex, inflatedPoint)
          pointIndex += 1
        inflatedMarkup.SetControlPointPositionsWorld(inflatedPoints)
        for pointIndex in range(len(pointIds)):
          inflatedMarkup.SetNthControlPointVisibility(pointIndex, False)
        inflatedMarkup.EndModify(wasModifying)

    if not self.updatingFromDerivedMarkup:
      pialControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, "Pial")
      if pialControlPoints is None:
        logging.error("Could not find inflated markup!")
      else:
        self.copyControlPoints(inputMarkupNode, origModel, self.origPointLocator, pialControlPoints, pialModel)

      inflatedControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, "Inflated")
      if inflatedControlPoints is None:
        logging.error("Could not find inflated markup!")
      else:
        self.copyControlPoints(inputMarkupNode, origModel, self.origPointLocator, inflatedControlPoints, inflatedModel)

    self.updatingFromMasterMarkup = False

  def copyControlPoints(self, sourceMarkup, sourceModel, sourceLocator, destinationMarkup, destinationModel, copyUndefinedControlPoints=True):
    if sourceMarkup is None or sourceModel is None or destinationMarkup is None or destinationModel is None:
      return
    if destinationModel and destinationModel.GetPolyData() and destinationModel.GetPolyData().GetPoints():
      wasModifying = destinationMarkup.StartModify()
      destinationMarkup.RemoveAllControlPoints()
      for i in range(sourceMarkup.GetNumberOfControlPoints()):
        if not copyUndefinedControlPoints and sourceMarkup.GetNthControlPointPositionStatus(i) != sourceMarkup.PositionDefined:
          continue
        sourcePoint = [0,0,0]
        sourceMarkup.GetNthControlPointPositionWorld(i, sourcePoint)
        sourceModel.TransformPointFromWorld(sourcePoint, sourcePoint)
        pointId = sourceLocator.FindClosestPoint(sourcePoint)
        destinationPoint = list(destinationModel.GetPolyData().GetPoints().GetPoint(pointId))
        destinationModel.TransformPointToWorld(destinationPoint, destinationPoint)
        destinationMarkup.AddControlPoint(vtk.vtkVector3d(destinationPoint))

      destinationMarkup.EndModify(wasModifying)

  def onDerivedControlPointsModified(self, derivedMarkupNode, eventId=None, node=None):
    if self.updatingFromMasterMarkup or self.updatingFromDerivedMarkup:
      return

    self.updatingFromDerivedMarkup = True
    origMarkup = derivedMarkupNode.GetNodeReference("OrigMarkup")
    origModel = self.parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)
    nodeType = derivedMarkupNode.GetAttribute("NeuroSegmentParcellation.NodeType")
    locator = None
    derivedModelNode = None
    otherMarkupNode = None
    otherModelNode = None
    if nodeType == "Pial":
      locator = self.pialPointLocator
      derivedModelNode = self.parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)

      otherMarkupNode = self.getDerivedControlPointsNode(origMarkup, "Inflated")
      otherModelNode = self.parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE)
    elif nodeType == "Inflated":
      locator = self.inflatedPointLocator
      derivedModelNode = self.parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE)

      otherMarkupNode = self.getDerivedControlPointsNode(origMarkup, "Pial")
      otherModelNode = self.parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
    if locator == None or derivedModelNode == None:
      self.updatingFromDerivedMarkup = False
      return

    copyUndefinedControlPoints = True
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    if interactionNode:
      copyUndefinedControlPoints = (interactionNode.GetCurrentInteractionMode() == interactionNode.Place)
    self.copyControlPoints(derivedMarkupNode, derivedModelNode, locator, origMarkup, origModel, copyUndefinedControlPoints)
    self.copyControlPoints(derivedMarkupNode, derivedModelNode, locator, otherMarkupNode, otherModelNode, copyUndefinedControlPoints)
    self.updatingFromDerivedMarkup = False

  @vtk.calldata_type(vtk.VTK_INT)
  def onDerivedCurvePointAdded(self, derivedCurveNode, eventId, controlPointIndex):
    if not derivedCurveNode or not derivedCurveNode.IsA("vtkMRMLMarkupsCurveNode"):
      return

    # TODO: We should be able to reverse engineer where this point should be inserted to be added to the "orig" curve
    return

  def getDerivedCurveNode(self, origMarkupNode, nodeType):
    if origMarkupNode is None:
      return None
    nodeReference = nodeType+"Curve"
    derivedMarkup = origMarkupNode.GetNodeReference(nodeReference)
    if derivedMarkup:
      return derivedMarkup

    derivedMarkup = slicer.mrmlScene.AddNewNodeByClass(origMarkupNode.GetClassName())
    derivedMarkup.CreateDefaultDisplayNodes()
    derivedMarkup.SetCurveTypeToLinear()
    derivedMarkup.UndoEnabledOff()
    derivedMarkup.SetLocked(True)
    derivedMarkup.GetDisplayNode().CopyContent(origMarkupNode.GetDisplayNode())
    derivedMarkup.SetName(origMarkupNode.GetName() + "_" + nodeReference)
    origMarkupNode.SetNodeReferenceID(nodeReference, derivedMarkup.GetID())
    derivedMarkup.SetNodeReferenceID("OrigMarkup", origMarkupNode.GetID())

    return derivedMarkup

  def getDerivedControlPointsNode(self, origMarkupNode, nodeType):
    if origMarkupNode is None:
      return None
    nodeReference = nodeType+"ControlPoints"
    derivedMarkup = origMarkupNode.GetNodeReference(nodeReference)
    if derivedMarkup:
      return derivedMarkup

    derivedMarkup = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
    derivedMarkup.CreateDefaultDisplayNodes()
    derivedMarkup.GetDisplayNode().CopyContent(origMarkupNode.GetDisplayNode())
    derivedMarkup.SetName(origMarkupNode.GetName() + "_" + nodeReference)
    derivedMarkup.SetAttribute("NeuroSegmentParcellation.NodeType", nodeType)
    origMarkupNode.SetNodeReferenceID(nodeReference, derivedMarkup.GetID())
    derivedMarkup.SetNodeReferenceID("OrigMarkup", origMarkupNode.GetID())

    return derivedMarkup

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    pass

  def parseParcellationString(self, parameterNode):
    queryString = self.getQueryString(parameterNode)
    if queryString is None:
      logging.error("Invalid query!")
      return

    success = False
    errorMessage = ""
    wasModifying = parameterNode.StartModify()
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    try:
      astNode = ast.parse(queryString)
      eq = NeuroSegmentParcellationVisitor()
      eq.setParameterNode(parameterNode)
      eq.visit(astNode)
      success = True
    except Exception as e:
      slicer.util.errorDisplay("Error parsing parcellation: "+str(e))
      import traceback
      traceback.print_exc()
      logging.error("Error parsing mesh tool string!")
    finally:
      slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)
      parameterNode.EndModify(wasModifying)
    return [success, errorMessage]

  def exportOutputToSegmentation(self, parameterNode, surfacesToExport=[]):
    if parameterNode is None:
      return

    numberOfOutputModels = parameterNode.GetNumberOfNodeReferences(OUTPUT_MODEL_REFERENCE)
    exportSegmentationNode = parameterNode.GetNodeReference(EXPORT_SEGMENTATION_REFERENCE)
    innerSurfaceNode = parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)
    outerSurfaceNode = parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
    for i in range(numberOfOutputModels):
      outputSurfaceNode = parameterNode.GetNthNodeReference(OUTPUT_MODEL_REFERENCE, i)
      if len(surfacesToExport) > 0 and not outputSurfaceNode.GetName() in surfacesToExport:
        continue
      self.exportMeshToSegmentation(outputSurfaceNode, innerSurfaceNode, outerSurfaceNode, exportSegmentationNode)
    exportSegmentationNode.CreateDefaultDisplayNodes()

  def exportMeshToSegmentation(self, surfacePatchNode, innerSurfaceNode, outerSurfaceNode, exportSegmentationNode):

    outputModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")

    toolNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLDynamicModelerNode")
    toolNode.SetToolName(slicer.vtkSlicerFreeSurferExtrudeTool().GetName())
    toolNode.SetNodeReferenceID("FreeSurferExtrude.InputPatch", surfacePatchNode.GetID())
    toolNode.SetNodeReferenceID("FreeSurferExtrude.InputOrigModel", innerSurfaceNode.GetID())
    toolNode.SetNodeReferenceID("FreeSurferExtrude.InputPialModel", outerSurfaceNode.GetID())
    toolNode.SetNodeReferenceID("FreeSurferExtrude.OutputModel", outputModelNode.GetID())
    slicer.modules.dynamicmodeler.logic().RunDynamicModelerTool(toolNode)
    slicer.mrmlScene.RemoveNode(toolNode)

    segmentName = surfacePatchNode.GetName()
    segmentColor = surfacePatchNode.GetDisplayNode().GetColor()
    segmentation = exportSegmentationNode.GetSegmentation()
    segmentation.SetMasterRepresentationName(slicer.vtkSegmentationConverter.GetClosedSurfaceRepresentationName())
    segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)
    segment = segmentation.GetSegment(segmentId)
    segmentIndex = segmentation.GetSegmentIndex(segmentId)
    if not segment is None:
      segmentation.RemoveSegment(segment)

    segment = slicer.vtkSegment()
    segment.SetName(segmentName)
    segment.SetColor(segmentColor)
    segment.AddRepresentation(slicer.vtkSegmentationConverter.GetClosedSurfaceRepresentationName(), outputModelNode.GetPolyData())
    segmentation.AddSegment(segment)
    segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)
    if segmentIndex >= 0:
      segmentation.SetSegmentIndex(segmentId, segmentIndex)
    slicer.mrmlScene.RemoveNode(outputModelNode)

  def initializePedigreeIds(self, parameterNode):
    """
    Add Pedigree Ids to Orig model cell data and point data
    """
    if parameterNode is None:
      logging.error("Invalid parameter node")
      return

    origModelNode = parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)
    if origModelNode is None or origModelNode.GetPolyData() is None:
      logging.error("Invalid Orig model")
      return

    polyData = origModelNode.GetPolyData()

    cellData = polyData.GetCellData()
    cellPedigreeArray = cellData.GetArray("cellPedigree")
    if cellPedigreeArray is None:
      cellPedigreeIds = vtk.vtkIdTypeArray()
      cellPedigreeIds.SetName("cellPedigree")
      cellPedigreeIds.SetNumberOfValues(polyData.GetNumberOfCells())
      for i in range(polyData.GetNumberOfCells()):
        cellPedigreeIds.SetValue(i, i)
      origModelNode.AddCellScalars(cellPedigreeIds)

    pointData = polyData.GetPointData()
    pointPedigreeArray = pointData.GetArray("pointPedigree")
    if pointPedigreeArray  is None:
      pointPedigreeIds = vtk.vtkIdTypeArray()
      pointPedigreeIds.SetName("pointPedigree")
      pointPedigreeIds.SetNumberOfValues(polyData.GetNumberOfPoints())
      for i in range(polyData.GetNumberOfPoints()):
        pointPedigreeIds.SetValue(i, i)
      origModelNode.AddPointScalars(pointPedigreeIds)

  def exportOutputToSurfaceLabel(self, parameterNode, surfacesToExport=[]):
    origSurfaceNode = parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)
    pialSurfaceNode = parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
    inflatedSurfaceNode = parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE)
    if origSurfaceNode is None or (origSurfaceNode is None and pialSurfaceNode is None and inflatedSurfaceNode is None):
      logging.error("exportOutputToSurfaceLabel: Invalid surface node")
      return

    cellCount = origSurfaceNode.GetPolyData().GetNumberOfCells()
    labelArray = origSurfaceNode.GetPolyData().GetCellData().GetArray("labels")
    if labelArray is None:
      labelArray = vtk.vtkIntArray()
      labelArray.SetName("labels")
      labelArray.SetNumberOfComponents(1)
      labelArray.SetNumberOfTuples(cellCount)
    labelArray.Fill(0)

    numberOfOutputModels = parameterNode.GetNumberOfNodeReferences(OUTPUT_MODEL_REFERENCE)
    for modelIndex in range(numberOfOutputModels):
      outputSurfaceNode = parameterNode.GetNthNodeReference(OUTPUT_MODEL_REFERENCE, modelIndex)
      if len(surfacesToExport) != 0 and not outputSurfaceNode.GetName() in surfacesToExport:
        continue

      polyData = outputSurfaceNode.GetPolyData()
      if polyData is None:
        continue

      cellData = polyData.GetCellData()
      cellPedigreeArray = cellData.GetArray("cellPedigree")
      if cellPedigreeArray is None:
        continue

      for cellIndex in range(cellPedigreeArray.GetNumberOfValues()):
        cellId = cellPedigreeArray.GetValue(cellIndex)
        labelArray.SetValue(cellId, modelIndex+1)

    # Update color table
    self.getParcellationColorNode()

    origSurfaceNode.GetPolyData().GetCellData().AddArray(labelArray)
    if pialSurfaceNode:
      pialSurfaceNode.GetPolyData().GetCellData().AddArray(labelArray)
    if inflatedSurfaceNode:
      inflatedSurfaceNode.GetPolyData().GetCellData().AddArray(labelArray)

  def getParcellationColorNode(self):
    parcellationColorNode = self.parameterNode.GetNodeReference("ParcellationColorNode")
    if parcellationColorNode is None:
      parcellationColorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "ParcellationColorNode")
      self.parameterNode.SetNodeReferenceID("ParcellationColorNode", parcellationColorNode.GetID())

    numberOfOutputModels = self.parameterNode.GetNumberOfNodeReferences(OUTPUT_MODEL_REFERENCE)
    lookupTable = vtk.vtkLookupTable()
    lookupTable.SetNumberOfColors(numberOfOutputModels + 1)
    lookupTable.SetTableValue(0, 0.1, 0.1, 0.1)
    labelValue = 1
    for i in range(numberOfOutputModels):
      outputSurfaceNode = self.parameterNode.GetNthNodeReference(OUTPUT_MODEL_REFERENCE, i)
      color = outputSurfaceNode.GetDisplayNode().GetColor()
      lookupTable.SetTableValue(labelValue, color[0], color[1], color[2])
      labelValue += 1
    parcellationColorNode.SetLookupTable(lookupTable)

    return parcellationColorNode

  def getQueryString(self, parameterNode):
    if parameterNode is None:
      return None
    queryTextNode = parameterNode.GetNodeReference(INPUT_QUERY_REFERENCE)
    if queryTextNode is None:
      return None
    return queryTextNode.GetText()


class NeuroSegmentParcellationVisitor(ast.NodeVisitor):
  """TODO
  """

  _parameterNode = None

  def __init__(self):
    pass

  def setParameterNode(self, parameterNode):
    self._parameterNode = parameterNode

  def visit_Assign(self, node):
    if len(node.targets) > 1:
        logging.error("Invalid assignment in line %d" % node.lineno)
        return

    if 'target' in node._fields:
      target = node.target
    if 'targets' in node._fields:
      target = node.targets[0]

    if not isinstance(target, ast.Name):
      logging.error("Invalid assignment in line %d" % node.lineno)
      return

    if target.id == "_Planes":
      self.process_InputNodes(node.value, "vtkMRMLMarkupsPlaneNode")
      return
    elif target.id == "_Curves":
      curveNodes = self.process_InputNodes(node.value, "vtkMRMLMarkupsCurveNode")
      for curveNode in curveNodes:
        curveNode.SetCurveTypeToShortestDistanceOnSurface()
      return
    elif target.id == "_ClosedCurves":
      curveNodes = self.process_InputNodes(node.value, "vtkMRMLMarkupsClosedCurveNode")
      for curveNode in curveNodes:
        curveNode.SetCurveTypeToShortestDistanceOnSurface()
      return
    elif target.id == "_DistanceWeightingFunction":
      self.distanceWeightingFunction = node.value.s
      return

    nodes = self.visit(node.value)

    outputModel = slicer.util.getFirstNodeByClassByName("vtkMRMLModelNode", target.id)
    if outputModel is None:
      outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", target.id)
    outputModelDisplayNode = outputModel.GetDisplayNode()
    if outputModelDisplayNode is None:
      outputModel.CreateDefaultDisplayNodes()
      outputModelDisplayNode = outputModel.GetDisplayNode()
      outputModelDisplayNode.SetVisibility(False)
    self._parameterNode.AddNodeReferenceID(OUTPUT_MODEL_REFERENCE, outputModel.GetID())

    toolNode = slicer.vtkMRMLDynamicModelerNode()
    slicer.mrmlScene.AddNode(toolNode)
    toolNode.SetName(outputModel.GetName() + "_BoundaryCut")
    toolNode.SetToolName(slicer.vtkSlicerDynamicModelerBoundaryCutTool().GetName())
    toolNode.SetNodeReferenceID("BoundaryCut.OutputModel", outputModel.GetID())
    for inputNode in nodes:
      toolNode.AddNodeReferenceID("BoundaryCut.InputBorder", inputNode.GetID())
    toolNode.ContinuousUpdateOff()
    self._parameterNode.AddNodeReferenceID(TOOL_NODE_REFERENCE, toolNode.GetID())

  def process_InputNodes(self, node, className):
    if not isinstance(node, ast.List):
      logging.error("Expected list of planes in line %d" % node.lineno)
      return
    planeNames = [e.id for e in node.elts]
    inputNodes = []
    for name in planeNames:
      inputNode = slicer.util.getFirstNodeByClassByName(className, name)
      if not inputNode:
        inputNode = slicer.mrmlScene.AddNewNodeByClass(className, name)
        inputNode.CreateDefaultDisplayNodes()
        displayNode = inputNode.GetDisplayNode()
        if displayNode:
          displayNode.SetGlyphScale(4.0)
          if className == "vtkMRMLMarkupsPlaneNode":
            displayNode.HandlesInteractiveOn()
      if inputNode.IsA("vtkMRMLMarkupsCurveNode"):
        inputNode.SetAttribute("DistanceWeightingFunction", self.distanceWeightingFunction)
        inputNodes.append(inputNode)
      self._parameterNode.AddNodeReferenceID(INPUT_MARKUPS_REFERENCE, inputNode.GetID())
    return inputNodes

  def visit_Name(self, node):
    slicerNode = slicer.util.getNode(node.id)
    return [slicerNode]

  def visit_Call(self, node):
    pass

  def visit_BinOp(self, node):
    leftValue = node.left
    rightValue = node.right
    if leftValue == None or rightValue == None:
      logging.error("Invalid binary operator arguments!")
      return

    leftNodes = self.visit(leftValue)
    rightNodes = self.visit(rightValue)
    return leftNodes + rightNodes

  def visit_UnaryOp(self, node):
    logging.error("Unary operator not supported!")

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

  def setupSphere(self):

    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetRadius(50.0)
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

    inputModelNode = self.setupSphere()

    logic = NeuroSegmentParcellationLogic()

    parcellationQueryNode = slicer.vtkMRMLTextNode()
    parcellationQueryNode.SetName("ParcellationQuery")
    slicer.mrmlScene.AddNode(parcellationQueryNode)

    storageNode = slicer.vtkMRMLTextStorageNode()
    storageNode.SetFileName(self.resourcePath('Parcellation/parcellation.qry'))
    storageNode.ReadData(parcellationQueryNode)
    slicer.mrmlScene.RemoveNode(storageNode)

    parameterNode = logic.getParameterNode()
    parameterNode.SetNodeReferenceID(ORIG_MODEL_REFERENCE, inputModelNode.GetID())
    parameterNode.SetNodeReferenceID(INPUT_QUERY_REFERENCE, parcellationQueryNode.GetID())

    logic.parseParcellationString(parameterNode)

    planeA = slicer.util.getNode("PlaneA")
    planeA.SetOrigin([0, 0, 0])
    planeA.SetNormal([0, 0, 1])

    planeB = slicer.util.getNode("PlaneB")
    planeB.SetOrigin([0, 0, 0])
    planeB.SetNormal([1, 0, 0])

    planeC = slicer.util.getNode("PlaneC")
    planeC.SetOrigin([0, 0, 0])
    planeC.SetNormal([0, 1, 0])

    testDuration = time.time() - startTime
    logging.info("Test duration: %f", testDuration)
