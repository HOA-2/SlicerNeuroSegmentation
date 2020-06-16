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

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.querySelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.origModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.pialModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.inflatedModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.exportSegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.applyButton.connect('checkBoxToggled(bool)', self.updateParameterNodeFromGUI)

    # Initial GUI update
    self.updateGUIFromParameterNode()
    self.updateOutputStructures()

  def enter(self):
    slicer.app.layoutManager().setLayout(NeuroSegmentParcellation.NEURO_PARCELLATION_LAYOUT_ID)
    slicer.util.getNode("ViewO").LinkedControlOn()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.logic.removeObservers()
    self.removeObservers()

  def setParameterNode(self, inputParameterNode):
    """
    Adds observers to the selected parameter node. Observation is needed because when the
    parameter node is changed then the GUI must be updated immediately.
    """
    self.logic.setParameterNode(inputParameterNode)

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

    parcellationQueryNode = slicer.util.getFirstNodeByClassByName("vtkMRMLTextNode", "ParcellationQuery")
    if parcellationQueryNode is None:
      parcellationQueryNode = slicer.vtkMRMLTextNode()
      parcellationQueryNode.SetName("ParcellationQuery")
      slicer.mrmlScene.AddNode(parcellationQueryNode)

      storageNode = slicer.vtkMRMLTextStorageNode()
      storageNode.SetFileName(self.resourcePath('Parcellation/parcellation.qry'))
      storageNode.ReadData(parcellationQueryNode)
      slicer.mrmlScene.RemoveNode(storageNode)
    if self._parameterNode is not None:
      self._parameterNode.SetNodeReferenceID(INPUT_QUERY_REFERENCE, parcellationQueryNode.GetID())

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """
    # Disable all sections if no parameter node is selected
    self.ui.inputQueryCollapsibleButton .enabled = self._parameterNode is not None
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

    wasBlocked = self.ui.querySelector.blockSignals(True)
    self.ui.querySelector.setCurrentNode(self._parameterNode.GetNodeReference(INPUT_QUERY_REFERENCE))
    self.ui.querySelector.blockSignals(wasBlocked)

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

    # Curve widgets
    inputCurvesLayout = qt.QFormLayout()
    for i in range(self._parameterNode.GetNumberOfNodeReferences(INPUT_MARKUPS_REFERENCE)):
      inputCurveNode = self._parameterNode.GetNthNodeReference(INPUT_MARKUPS_REFERENCE, i)
      if inputCurveNode.IsA("vtkMRMLMarkupsCurveNode"):
        placeWidget = slicer.qSlicerMarkupsPlaceWidget()
        placeWidget.setMRMLScene(slicer.mrmlScene)
        placeWidget.setCurrentNode(inputCurveNode)
        inputCurvesLayout.addRow(qt.QLabel(inputCurveNode.GetName()), placeWidget)

    self._inputCurvesWidget = qt.QWidget()
    self._inputCurvesWidget.setLayout(inputCurvesLayout)
    self.ui.inputCurvesCollapsibleButton.layout().addWidget(self._inputCurvesWidget)

    # Plane widgets
    inputPlanesLayout = qt.QFormLayout()
    for i in range(self._parameterNode.GetNumberOfNodeReferences(INPUT_MARKUPS_REFERENCE)):
      inputPlaneNode = self._parameterNode.GetNthNodeReference(INPUT_MARKUPS_REFERENCE, i)
      if inputPlaneNode.IsA("vtkMRMLMarkupsPlaneNode"):
        placeWidget = slicer.qSlicerMarkupsPlaceWidget()
        placeWidget.setMRMLScene(slicer.mrmlScene)
        placeWidget.setCurrentNode(inputPlaneNode)
        inputPlanesLayout.addRow(qt.QLabel(inputPlaneNode.GetName()), placeWidget)

    self._inputPlanesWidget = qt.QWidget()
    self._inputPlanesWidget.setLayout(inputPlanesLayout)
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

      visibilityButton = qt.QPushButton()
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

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """
    if self._parameterNode is None:
      return

    sliceViewIDs = ["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow"]
    origModel = self.ui.origModelSelector.currentNode()
    if not origModel is None:
      origViews = sliceViewIDs[:]
      origViews.append("vtkMRMLViewNodeO")
      origModel.GetDisplayNode().SetViewNodeIDs(origViews)
    pialModel = self.ui.pialModelSelector.currentNode()
    if not pialModel is None:
      pialViews = sliceViewIDs[:]
      pialViews.append("vtkMRMLViewNodeP")
      pialModel.GetDisplayNode().SetViewNodeIDs(pialViews)
    inflatedModel = self.ui.inflatedModelSelector.currentNode()
    if not inflatedModel is None:
      inflatedViews = sliceViewIDs[:]
      inflatedViews.append("vtkMRMLViewNodeI")
      inflatedModel.GetDisplayNode().SetViewNodeIDs(inflatedViews)

    wasModifying = self._parameterNode.StartModify()
    self._parameterNode.SetNodeReferenceID(INPUT_QUERY_REFERENCE, self.ui.querySelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(ORIG_MODEL_REFERENCE, self.ui.origModelSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(PIAL_MODEL_REFERENCE, self.ui.pialModelSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(INFLATED_MODEL_REFERENCE, self.ui.inflatedModelSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(EXPORT_SEGMENTATION_REFERENCE, self.ui.exportSegmentationSelector.currentNodeID)
    numberOfToolNodes = self._parameterNode.GetNumberOfNodeReferences(TOOL_NODE_REFERENCE)
    for i in range(numberOfToolNodes):
      toolNode = self._parameterNode.GetNthNodeReference(TOOL_NODE_REFERENCE, i)
      toolNode.SetContinuousUpdate(self.ui.applyButton.checked)
    self._parameterNode.EndModify(wasModifying)

  def onApplyButton(self):
    """
    Apply all of the parcellation tools
    """
    if self._parameterNode is None:
      return
    numberOfToolNodes = self._parameterNode.GetNumberOfNodeReferences(TOOL_NODE_REFERENCE)
    dynamicModelerLogic = slicer.modules.dynamicmodeler.logic()
    for i in range(numberOfToolNodes):
      toolNode = self._parameterNode.GetNthNodeReference(TOOL_NODE_REFERENCE, i)
      dynamicModelerLogic.RunDynamicModelerTool(toolNode)

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

  def onLoadQuery(self):
    """
    Setup nodes
    """
    if self._parameterNode is None:
      return
    self.ui.loadQueryButton.setIcon(qt.QIcon())
    self.ui.loadQueryButton.setToolTip("")

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
    self.inputMarkupObservers = []
    self.parameterNode = None

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.updateParameterNodeObservers)
    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)
    self.updateParameterNodeObservers()

  def setParameterNode(self, parameterNode):
    """Set the current parameter node and initialize all unset parameters to their default values"""
    if self.parameterNode==parameterNode:
      return
    self.parameterNode = parameterNode

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
    self.addObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)

  def onParameterNodeModified(self, parameterNode, eventId=None):
    if parameterNode is None:
      return
    self.updateInputMarkupObservers(parameterNode)

    inputModelNode = parameterNode.GetNodeReference(ORIG_MODEL_REFERENCE)
    if inputModelNode is not None:
      if self.origPointLocator.GetDataSet() != inputModelNode.GetPolyData():
        self.origPointLocator.SetDataSet(inputModelNode.GetPolyData())
        self.origPointLocator.BuildLocator()

      numberOfToolNodes = parameterNode.GetNumberOfNodeReferences(TOOL_NODE_REFERENCE)
      for i in range(numberOfToolNodes):
        toolNode = parameterNode.GetNthNodeReference(TOOL_NODE_REFERENCE, i)
        if toolNode.GetNodeReference("BoundaryCut.InputModel") != inputModelNode:
          toolNode.SetNodeReferenceID("BoundaryCut.InputModel", inputModelNode.GetID())

      numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(INPUT_MARKUPS_REFERENCE)
      for i in range(numberOfMarkupNodes):
        inputCurveNode = parameterNode.GetNthNodeReference(INPUT_MARKUPS_REFERENCE, i)
        if inputCurveNode.IsA("vtkMRMLMarkupsCurveNode"):
          inputCurveNode.SetAndObserveShortestDistanceSurfaceNode(inputModelNode)

  def removeInputMarkupObservers(self):
    for obj, tag in self.inputMarkupObservers:
      obj.RemoveObserver(tag)
    self.inputMarkupObservers = []

  def updateInputMarkupObservers(self, parameterNode):
    if parameterNode is None:
      return
    numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfMarkupNodes):
      inputMarkupNode = parameterNode.GetNthNodeReference(INPUT_MARKUPS_REFERENCE, i)
      if not inputMarkupNode.IsA("vtkMRMLMarkupsCurveNode"):
        continue
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointEndInteractionEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      inputMarkupNode.GetDisplayNode().SetViewNodeIDs(["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", "vtkMRMLViewNodeO"])

  @vtk.calldata_type(vtk.VTK_INT)
  def onMasterMarkupModified(self, inputMarkupNode, eventId=None, node=None):
    origModel = self.parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
    curvePoints = inputMarkupNode.GetCurve().GetPoints()
    if self.origPointLocator.GetDataSet() is None or curvePoints is None:
      return

    pointIds = []
    for i in range(curvePoints.GetNumberOfPoints()):
      origPoint = list(curvePoints.GetPoint(i))
      origModel.TransformPointFromWorld(origPoint, origPoint)
      pointIds.append(self.origPointLocator.FindClosestPoint(origPoint))

    pialMarkup = self.getDerivedMarkupNode(inputMarkupNode, "PialMarkup")
    if pialMarkup is None:
      logging.error("Could not find pial markup!")
    else:
      curvePoints = inputMarkupNode.GetCurve().GetPoints()
      wasModifying = pialMarkup.StartModify()
      pialMarkup.RemoveAllControlPoints()
      pialModel = self.parameterNode.GetNodeReference(PIAL_MODEL_REFERENCE)
      if pialModel and pialModel.GetPolyData() and pialModel.GetPolyData().GetPoints():
        for pointId in pointIds:
          pialPoint = list(pialModel.GetPolyData().GetPoints().GetPoint(pointId))
          pialModel.TransformPointToWorld(pialPoint, pialPoint )
          controlPointID = pialMarkup.AddControlPointWorld(vtk.vtkVector3d(pialPoint))
          pialMarkup.SetNthControlPointVisibility(controlPointID, False)
      pialMarkup.EndModify(wasModifying)

    inflatedMarkup = self.getDerivedMarkupNode(inputMarkupNode, "InflatedMarkup")
    if inflatedMarkup is None:
      logging.error("Could not find inflated markup!")
    else:
      curvePoints = inputMarkupNode.GetCurve().GetPoints()
      wasModifying = inflatedMarkup.StartModify()
      inflatedMarkup.RemoveAllControlPoints()
      inflatedModel = self.parameterNode.GetNodeReference(INFLATED_MODEL_REFERENCE)
      if inflatedModel and inflatedModel.GetPolyData() and inflatedModel.GetPolyData().GetPoints():
        for pointId in pointIds:
          inflatedPoint = list(inflatedModel.GetPolyData().GetPoints().GetPoint(pointId))
          inflatedModel.TransformPointToWorld(inflatedPoint, inflatedPoint )
          controlPointID = inflatedMarkup.AddControlPointWorld(vtk.vtkVector3d(inflatedPoint))
          inflatedMarkup.SetNthControlPointVisibility(controlPointID, False)
      inflatedMarkup.EndModify(wasModifying)

  def getDerivedMarkupNode(self, origMarkupNode, nodeType):
    if origMarkupNode is None:
      return None
    derivedMarkup = origMarkupNode.GetNodeReference(nodeType)
    if not derivedMarkup is None:
      return derivedMarkup

    derivedMarkup = slicer.mrmlScene.AddNewNodeByClass(origMarkupNode.GetClassName())
    derivedMarkup.SetCurveTypeToLinear()
    derivedMarkup.CreateDefaultDisplayNodes()
    derivedMarkup.GetDisplayNode().CopyContent(origMarkupNode.GetDisplayNode())
    derivedMarkup.SetName(origMarkupNode.GetName() + "_" + nodeType)
    origMarkupNode.SetNodeReferenceID(nodeType, derivedMarkup.GetID())

    sliceViewIDs = ["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow"]
    viewIDs = sliceViewIDs[:]
    if nodeType == "PialMarkup":
      viewIDs.append("vtkMRMLViewNodeP")
    if nodeType == "InflatedMarkup":
      viewIDs.append("vtkMRMLViewNodeI")
    derivedMarkup.GetDisplayNode().SetViewNodeIDs(viewIDs)

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
    except SyntaxError as e:
      logging.error("Error parsing mesh tool string!")
      errorMessage = str(e)
      logging.error(errorMessage)
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

    nodes = self.visit(node.value)

    outputModel = slicer.util.getFirstNodeByClassByName("vtkMRMLModelNode", target.id)
    if outputModel is None:
      outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", target.id)
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
    #storageNode.SetFileName(self.resourcePath('Parcellation/parcellation.qry'))
    storageNode.ReadData(parcellationQueryNode)
    slicer.mrmlScene.RemoveNode(storageNode)

    parameterNode = logic.getParameterNode()
    parameterNode.SetNodeReferenceID(ORIG_MODEL_REFERENCE, inputModelNode.GetID())
    parameterNode.SetNodeReferenceID(INPUT_QUERY_REFERENCE, parcellationQueryNode.GetID())
    parameterNode.SetAttribute("TEST", inputModelNode.GetID())

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
