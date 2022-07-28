import vtk, qt, ctk, slicer
import os
from slicer.util import VTKObservationMixin
import logging

class NeuroSegmentOutputToolWidget(qt.QWidget, VTKObservationMixin):
  def __init__(self, logic):
    qt.QWidget.__init__(self)
    VTKObservationMixin.__init__(self)
    self.logic = logic

    self.isUpdatingGUIFromMRML = False
    self.toolNode = None
    self.parameterNode = None
    self.modifiedDuringImport = False

    self.inputBorderSelectors = []
    self.inputBorderReference = "BoundaryCut.InputBorder"

    self.deleted = False

    self.setup()

  def setup(self):
    """
    Setup the widget UI
    """

    contentsLayout = qt.QHBoxLayout()
    contentsLayout.setContentsMargins(0, 0, 0, 0)
    contentsLayout.setSpacing(0)
    self.setLayout(contentsLayout)
    self.setContentsMargins(0, 0, 0, 0)

    self.advancedFrame = None

    moduleName = "NeuroSegmentParcellation"
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(moduleName))
    uiPath = os.path.join(scriptedModulesPath, 'Resources', 'UI', 'NeuroSegmentOutputToolWidget.ui')
    self.uiWidget = slicer.util.loadUI(uiPath)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.EndImportEvent, self.onSceneImportEnd)

    self.updateGUIFromMRML()
    self.layout().addWidget(self.uiWidget)

    self.ui.colorPicker.connect('colorChanged(QColor)', self.onColorChanged)
    self.connect('destroyed(QObject*)', self.onDestroyed)

    self.ui.visibilityButton.connect('clicked(bool)', self.onVisibilityClicked)

    self.ui.computeButton.connect('clicked(bool)', self.onComputeClicked)
    self.ui.deleteButton.connect('clicked(bool)', self.onDeleteClicked)

    self.ui.advancedGroupBox.connect('toggled(bool)', self.updateAdvancedSection)

  def onDestroyed(self):
    self.removeObservers()
    self.deleted = True

  def setParameterNode(self, parameterNode):
    self.parameterNode = parameterNode

  def setToolNode(self, toolNode):
    """
    Set and observe the current parameter node.
    """
    if self.toolNode == toolNode:
      return

    self.toolNode = toolNode
    self.removeObservers(self.onToolNodeModified)

    if self.toolNode:
      self.addObserver(self.toolNode, vtk.vtkCommand.ModifiedEvent, self.onToolNodeModified)

    self.onToolNodeModified()

  def onSceneImportEnd(self, toolNode=None, event=None):
    """
    Called when scene import is finished.
    If modifiedDuringImport was set to True during import, then the widget needs to be updated.
    """
    if self.modifiedDuringImport:
      self.onToolNodeModified()
    self.modifiedDuringImport = False

  def onToolNodeModified(self, toolNode=None, event=None):
    """
    Method invoked when the observed tool node is modified.
    """
    if self.deleted:
      return

    if slicer.mrmlScene.IsImporting():
      self.modifiedDuringImport = True
      return

    outputModelDisplayNode = self.getOutputModelDisplayNode()
    if outputModelDisplayNode and not self.hasObserver(outputModelDisplayNode, vtk.vtkCommand.ModifiedEvent, self.onOutputModelDisplayModified):
      self.removeObservers(self.onOutputModelDisplayModified)
      self.addObserver(outputModelDisplayNode, vtk.vtkCommand.ModifiedEvent, self.onOutputModelDisplayModified)
      self.onOutputModelDisplayModified()
    elif outputModelDisplayNode is None:
      self.removeObservers(self.onOutputModelDisplayModified)

    self.updateGUIFromMRML()

  def onOutputModelDisplayModified(self, displayNode=None, event=None):
    """
    Method when the ModifiedEvent is invoked on the output model display node.
    """
    if slicer.mrmlScene.IsImporting():
      self.modifiedDuringImport = True
      return

    self.updateGUIFromMRML()

  def onColorChanged(self):
    """
    Method called when the color picker is changed by the user.
    """
    if self.isUpdatingGUIFromMRML:
      return

    displayNode = self.getOutputModelDisplayNode()
    if displayNode is None:
      logging.error("onColorChanged: Invalid display node")
      return

    color = self.ui.colorPicker.color
    newColor = [color.red()/255.0, color.green()/255.0, color.blue()/255.0]
    logging.info("onColorChanged: Color changed: " + str(newColor))
    displayNode.SetColor(newColor[0], newColor[1], newColor[2])

  def onVisibilityClicked(self):
    """
    Method called when the visibility button is clicked.
    """
    if self.isUpdatingGUIFromMRML:
      return
    modelNode = self.getOutputModelNode()
    if modelNode is None:
      logging.error("onVisibilityClicked: Invalid model node")
      return
    modelNode.SetDisplayVisibility(not modelNode.GetDisplayVisibility())

  def onComputeClicked(self):
    if self.toolNode is None:
      logging.error("onComputeClicked: Invalid tool node")
      return
    logging.info(f"Computing: {self.toolNode.GetName()}")
    self.logic.runDynamicModelerTool(self.toolNode)
    self.logic.exportOutputToSurfaceLabel(self.parameterNode)

  def onDeleteClicked(self):
    outputModelNode = self.getOutputModelNode()
    if outputModelNode is None:
      logging.error("onDeleteClicked: Invalid tool node")
      return
    logging.info(f"Deleting: {self.toolNode.GetName()}")
    outputModelNode.SetAndObservePolyData(vtk.vtkPolyData())

  def getOutputModelNode(self):
    if self.toolNode is None:
      return None
    return self.toolNode.GetNodeReference("BoundaryCut.OutputModel")

  def getOutputModelDisplayNode(self):
    outputModelNode = self.getOutputModelNode()
    if outputModelNode is None:
      return None
    outputModelNode.CreateDefaultDisplayNodes()
    return outputModelNode.GetDisplayNode()

  def updateGUIFromMRML(self):
    """
    Update the GUI from the plan node.
    """
    if self.deleted:
      return

    if self.isUpdatingGUIFromMRML:
      return
    self.isUpdatingGUIFromMRML = True

    self.uiWidget.enabled = not self.toolNode is None

    color = [0,0,0]
    outputModelDisplayNode = self.getOutputModelDisplayNode()
    if outputModelDisplayNode:
      color = outputModelDisplayNode.GetColor()
    self.ui.colorPicker.setColor(qt.QColor(color[0]*255, color[1]*255, color[2]*255))

    visible = False
    modelNode = self.getOutputModelNode()
    if modelNode:
      visible = modelNode.GetDisplayVisibility()
    if visible:
      self.ui.visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
    else:
      self.ui.visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerInvisible.png"))

    outputExists = modelNode and modelNode.GetPolyData() and modelNode.GetPolyData().GetNumberOfPoints() > 0
    self.ui.computeButton.visible = not outputExists
    self.ui.deleteButton.visible  =     outputExists

    self.updateAdvancedSection()

    self.isUpdatingGUIFromMRML = False

  def updateAdvancedSection(self):

    self.inputBorderSelectors = []

    if self.advancedFrame:
      self.ui.advancedGroupBox.layout().removeWidget(self.advancedFrame)
      self.advancedFrame.deleteLater()
      self.advancedFrame = None

    if self.ui.advancedGroupBox.collapsed:
      # To reduce the number of comboboxes that need to be updated,
      # only create the widgets when the advanced group box is open.
      return

    advancedFrameLayout = qt.QFormLayout()
    self.advancedFrame = qt.QFrame()
    self.advancedFrame.setLayout(advancedFrameLayout)

    seedPlaceWidget = slicer.qSlicerMarkupsPlaceWidget()
    seedPlaceWidget.setCurrentNode(self.logic.getInputSeedNode(self.toolNode))
    seedPlaceWidget.setMRMLScene(slicer.mrmlScene)
    advancedFrameLayout.addRow(qt.QLabel(f"Seed node:"), seedPlaceWidget)

    comboBoxClasses = ["vtkMRMLMarkupsCurveNode", "vtkMRMLMarkupsPlaneNode"]

    numberOfNodeReferences = 0
    if self.toolNode:
      numberOfNodeReferences = self.toolNode.GetNumberOfNodeReferences(self.inputBorderReference)
    i = 0
    for i in range(numberOfNodeReferences):
      inputNode = self.toolNode.GetNthNodeReference(self.inputBorderReference, i)
      comboBox = self.createComboBox(inputNode, comboBoxClasses)
      advancedFrameLayout.addRow(qt.QLabel(f"Input {i}:"), comboBox)
      self.inputBorderSelectors.append(comboBox)
    comboBox = self.createComboBox(None, comboBoxClasses)
    advancedFrameLayout.addRow(qt.QLabel(f"Input {i+1}:"), comboBox)
    self.inputBorderSelectors.append(comboBox)

    self.ui.advancedGroupBox.layout().addWidget(self.advancedFrame)

  def createComboBox(self, inputNode, nodeClasses):
    comboBox = slicer.qMRMLNodeComboBox()
    comboBox.addEnabled = False
    comboBox.removeEnabled = False
    comboBox.renameEnabled = False
    comboBox.noneEnabled= True
    comboBox.nodeTypes = nodeClasses
    comboBox.setMRMLScene(slicer.mrmlScene)
    comboBox.setCurrentNode(inputNode)
    comboBox.connect('currentNodeChanged(vtkMRMLNode*)', self.updateToolReferences)
    return comboBox

  def updateToolReferences(self):
    with slicer.util.NodeModify(self.toolNode):
      self.toolNode.RemoveNodeReferenceIDs(self.inputBorderReference)
      for nodeSelector in self.inputBorderSelectors:
        currentNode = nodeSelector.currentNode()
        if currentNode is None:
          continue
        self.toolNode.AddNodeReferenceID(self.inputBorderReference, currentNode.GetID())
