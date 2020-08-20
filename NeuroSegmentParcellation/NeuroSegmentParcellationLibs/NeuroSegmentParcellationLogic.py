import os
import ast
import vtk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging

from NeuroSegmentParcellationLibs.NeuroSegmentParcellationVisitor import NeuroSegmentParcellationVisitor

class NeuroSegmentParcellationLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):
  """Perform filtering
  """

  # Boundary cut references
  BOUNDARY_CUT_INPUT_BORDER_REFERENCE = "BoundaryCut.InputBorder"
  BOUNDARY_CUT_OUTPUT_MODEL_REFERENCE = "BoundaryCut.OutputModel"
  BOUNDARY_CUT_INPUT_SEED_REFERENCE = "BoundaryCut.InputSeed"

  ANTERIOR_OF_RELATIVE_ROLE = "anterior_of"
  POSTERIOR_OF_RELATIVE_ROLE = "posterior_of"
  SUPERIOR_OF_RELATIVE_ROLE = "superior_of"
  INFERIOR_OF_RELATIVE_ROLE = "inferior_of"
  MEDIAL_OF_RELATIVE_ROLE = "medial_of"
  LATERAL_OF_RELATIVE_ROLE = "lateral_of"

  RELATIVE_SEED_ROLES = [
    ANTERIOR_OF_RELATIVE_ROLE,
    POSTERIOR_OF_RELATIVE_ROLE,
    SUPERIOR_OF_RELATIVE_ROLE,
    INFERIOR_OF_RELATIVE_ROLE,
    MEDIAL_OF_RELATIVE_ROLE,
    LATERAL_OF_RELATIVE_ROLE,
  ]
  RELATIVE_NODE_REFERENCE = "Relative"

  INPUT_MARKUPS_REFERENCE = "InputMarkups"
  ORIG_MODEL_REFERENCE = "OrigModel"
  PIAL_MODEL_REFERENCE = "PialModel"
  INFLATED_MODEL_REFERENCE = "InflatedModel"
  INPUT_QUERY_REFERENCE = "InputQuery"
  OUTPUT_MODEL_REFERENCE = "OutputModel"
  TOOL_NODE_REFERENCE = "ToolNode"
  EXPORT_SEGMENTATION_REFERENCE = "ExportSegmentation"

  ORIG_NODE_ATTRIBUTE_VALUE = "Orig"
  PIAL_NODE_ATTRIBUTE_VALUE = "Pial"
  INFLATED_NODE_ATTRIBUTE_VALUE = "Inflated"

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    VTKObservationMixin.__init__(self)
    self.isSingletonParameterNode = False
    self.queryNodeFileName = ""

    self.origPointLocator = vtk.vtkPointLocator()
    self.pialPointLocator = vtk.vtkPointLocator()
    self.inflatedPointLocator = vtk.vtkPointLocator()
    self.inputMarkupObservers = []
    self.parameterNode = None
    self.updatingFromMasterMarkup = False
    self.updatingFromDerivedMarkup = False
    self.updatingSeedNodes = False

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

  def setQueryNodeFileName(self, fileName):
    self.queryNodeFileName = fileName

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

    self.updateInputModelNodes(parameterNode)
    self.updateInputModelPointLocators(parameterNode)
    self.updateAllModelViews(parameterNode)

    self.removeInputMarkupObservers()
    self.updateInputMarkupDisplay(parameterNode)
    self.updateInputMarkupSurfaceCostFunction(parameterNode)
    self.updateInputMarkupObservers(parameterNode)

  def updateInputModelNodes(self, parameterNode):
    origModelNode = parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
    numberOfToolNodes = parameterNode.GetNumberOfNodeReferences(self.TOOL_NODE_REFERENCE)
    for i in range(numberOfToolNodes):
      toolNode = parameterNode.GetNthNodeReference(self.TOOL_NODE_REFERENCE, i)
      if origModelNode is None:
        toolNode.RemoveNodeReferenceIDs("BoundaryCut.InputModel")
      elif toolNode.GetNodeReference("BoundaryCut.InputModel") != origModelNode:
        toolNode.SetNodeReferenceID("BoundaryCut.InputModel", origModelNode.GetID())

  def updateInputMarkupSurfaceCostFunction(self, parameterNode):
    origModelNode = parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
    numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(self.INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfMarkupNodes):
      inputCurveNode = parameterNode.GetNthNodeReference(self.INPUT_MARKUPS_REFERENCE, i)
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

    self.updateModelViews(parameterNode, self.ORIG_MODEL_REFERENCE, "vtkMRMLViewNodeO")
    self.updateModelViews(parameterNode, self.PIAL_MODEL_REFERENCE, "vtkMRMLViewNodeP")
    self.updateModelViews(parameterNode, self.INFLATED_MODEL_REFERENCE, "vtkMRMLViewNodeI")
    self.updateModelViews(parameterNode, self.OUTPUT_MODEL_REFERENCE, "vtkMRMLViewNodeO")

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

  def updateInputModelPointLocators(self, parameterNode):
    if parameterNode is None:
      return

    origModelNode = parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
    if origModelNode is not None and self.origPointLocator.GetDataSet() != origModelNode.GetPolyData():
        self.origPointLocator.SetDataSet(origModelNode.GetPolyData())
        self.origPointLocator.BuildLocator()

    pialModelNode = parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)
    if pialModelNode is not None and self.pialPointLocator.GetDataSet() != pialModelNode.GetPolyData():
        self.pialPointLocator.SetDataSet(pialModelNode.GetPolyData())
        self.pialPointLocator.BuildLocator()

    inflatedModelNode = parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)
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
    if parameterNode is None:
      return

    inputMarkupNodes = self.getInputMarkupNodes()
    for inputMarkupNode in inputMarkupNodes:
      if inputMarkupNode is None:
        continue
      if inputMarkupNode.IsA("vtkMRMLMarkupsCurveNode"):
        tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onMasterMarkupModified)
        self.inputMarkupObservers.append((inputMarkupNode, tag))
        tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onMasterMarkupModified)
        self.inputMarkupObservers.append((inputMarkupNode, tag))
        tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onMasterMarkupModified)
        self.inputMarkupObservers.append((inputMarkupNode, tag))
        tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.LockModifiedEvent, self.onMarkupLockStateModified)
        self.inputMarkupObservers.append((inputMarkupNode, tag))
        tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.DisplayModifiedEvent, self.onMasterMarkupDisplayModified)
        self.inputMarkupObservers.append((inputMarkupNode, tag))
        inputMarkupNode.SetAttribute("NeuroSegmentParcellation.NodeType", self.ORIG_NODE_ATTRIBUTE_VALUE)
        self.onMarkupLockStateModified(inputMarkupNode)

      pialControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
      if pialControlPoints:
        tag = pialControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((pialControlPoints, tag))
        tag = pialControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((pialControlPoints, tag))

      inflatedControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
      if inflatedControlPoints:
        tag = inflatedControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((inflatedControlPoints, tag))
        tag = inflatedControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((inflatedControlPoints, tag))

    toolNodes = self.getToolNodes()
    for toolNode in toolNodes:
      seedNode = self.getInputSeedNode(toolNode)
      if seedNode is None:
        continue
      tag = seedNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onSeedNodeModified)
      self.inputMarkupObservers.append((seedNode, tag))
      tag = seedNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onSeedRemoved)
      self.inputMarkupObservers.append((seedNode, tag))

  def updateInputMarkupDisplay(self, parameterNode):
    if parameterNode is None:
      return

    origMarkupViews = self.getMarkupViewIDs(parameterNode, self.ORIG_NODE_ATTRIBUTE_VALUE)
    pialMarkupViews = self.getMarkupViewIDs(parameterNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
    inflatedMarkupViews = self.getMarkupViewIDs(parameterNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)

    projectionEnabled = self.getMarkupProjectionEnabled(parameterNode)
    startFade = 0.0
    endFade = 0.5
    if projectionEnabled:
      startFade = 1.0
      endFade = 10.0

    numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(self.INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfMarkupNodes):
      inputMarkupNode = parameterNode.GetNthNodeReference(self.INPUT_MARKUPS_REFERENCE, i)
      inputMarkupNode.GetDisplayNode().SetViewNodeIDs(origMarkupViews)
      inputMarkupNode.GetDisplayNode().SetLineColorFadingStart(startFade)
      inputMarkupNode.GetDisplayNode().SetLineColorFadingEnd(endFade)

      if inputMarkupNode is None or not inputMarkupNode.IsA("vtkMRMLMarkupsCurveNode"):
        continue

      pialControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
      if pialControlPoints:
        pialControlPoints.GetDisplayNode().SetViewNodeIDs(pialMarkupViews)

      inflatedControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
      if inflatedControlPoints:
        inflatedControlPoints.GetDisplayNode().SetViewNodeIDs(inflatedMarkupViews)

      pialCurveNode = self.getDerivedCurveNode(inputMarkupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
      if pialCurveNode:
        pialCurveNode.GetDisplayNode().SetViewNodeIDs(pialMarkupViews)
        pialCurveNode.GetDisplayNode().SetLineColorFadingStart(startFade)
        pialCurveNode.GetDisplayNode().SetLineColorFadingEnd(endFade)

      inflatedCurveNode = self.getDerivedCurveNode(inputMarkupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
      if inflatedCurveNode:
        inflatedCurveNode.GetDisplayNode().SetViewNodeIDs(inflatedMarkupViews)
        inflatedCurveNode.GetDisplayNode().SetLineColorFadingStart(startFade)
        inflatedCurveNode.GetDisplayNode().SetLineColorFadingEnd(endFade)

      numberOfToolNodes = parameterNode.GetNumberOfNodeReferences(self.TOOL_NODE_REFERENCE)
      for i in range(numberOfToolNodes):
        toolNode = parameterNode.GetNthNodeReference(self.TOOL_NODE_REFERENCE, i)
        inputSeed = toolNode.GetNodeReference(self.BOUNDARY_CUT_INPUT_SEED_REFERENCE)
        if inputSeed:
          inputSeed.GetDisplayNode().SetViewNodeIDs(origMarkupViews)

  def onMasterMarkupModified(self, inputMarkupNode, eventId=None, callData=None):
    if self.updatingFromMasterMarkup or self.parameterNode is None:
      return

    origModel = self.parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)
    if origModel is None:
      return

    curvePoints = inputMarkupNode.GetCurve().GetPoints()
    if self.origPointLocator.GetDataSet() is None or curvePoints is None:
      return

    wasUpdatingFromMasterMarkup = self.updatingFromMasterMarkup
    self.updatingFromMasterMarkup = True

    pointIds = []
    for i in range(curvePoints.GetNumberOfPoints()):
      origPoint = list(curvePoints.GetPoint(i))
      origModel.TransformPointFromWorld(origPoint, origPoint)
      pointIds.append(self.origPointLocator.FindClosestPoint(origPoint))

    pialMarkup = self.getDerivedCurveNode(inputMarkupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
    if pialMarkup:
      with slicer.util.NodeModify(pialMarkup):
        pialModel = self.parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)
        if pialModel and pialModel.GetPolyData() and pialModel.GetPolyData().GetPoints():
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

    inflatedMarkup = self.getDerivedCurveNode(inputMarkupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
    if inflatedMarkup:
      with slicer.util.NodeModify(inflatedMarkup):
        inflatedModel = self.parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)
        if inflatedModel and inflatedModel.GetPolyData() and inflatedModel.GetPolyData().GetPoints():
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

    if not self.updatingFromDerivedMarkup:
      pialControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
      if pialControlPoints is None:
        logging.error("Could not find inflated markup!")
      else:
        self.copyControlPoints(inputMarkupNode, origModel, self.origPointLocator, pialControlPoints, pialModel)

      inflatedControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
      if inflatedControlPoints is None:
        logging.error("Could not find inflated markup!")
      else:
        self.copyControlPoints(inputMarkupNode, origModel, self.origPointLocator, inflatedControlPoints, inflatedModel)

    self.updatingFromMasterMarkup = wasUpdatingFromMasterMarkup

  def onSeedNodeModified(self, seedNode, eventId=None, callData=None):
    if self.updatingSeedNodes:
      return
    seedNode.SetAttribute("ManuallyPlaced", "TRUE")

  def onSeedRemoved(self, seedNode, eventId=None, callData=None):
    if seedNode is None:
      return
    if seedNode.GetNumberOfControlPoints() != 0:
      return
    seedNode.SetAttribute("ManuallyPlaced", "FALSE")

  def updateRelativeSeedsForMarkup(self, markupNode):
    if markupNode is None:
      logging.error("updateRelativeSeedsForMarkup: Invalid markupNode")
      return
    seedNodes = self.getRelativeSeedNodes(markupNode)
    for seedNode in seedNodes:
      self.updateRelativeSeedNode(seedNode)

  def snapSeedsToSurface(self, seedNode):
    dataSet = self.origPointLocator.GetDataSet()
    if dataSet is None:
      return
    for i in range(seedNode.GetNumberOfControlPoints()):
      controlPoint = [0.0, 0.0, 0.0]
      seedNode.GetNthControlPointPosition(i, controlPoint)
      pointId = self.origPointLocator.FindClosestPoint(controlPoint)
      dataSet.GetPoint(pointId, controlPoint)
      seedNode.SetNthControlPointPosition(i, controlPoint[0], controlPoint[1], controlPoint[2])

  def copyControlPoints(self, sourceMarkup, sourceModel, sourceLocator, destinationMarkup, destinationModel, copyUndefinedControlPoints=True):
    if sourceMarkup is None or sourceModel is None or destinationMarkup is None or destinationModel is None:
      return
    if destinationModel and destinationModel.GetPolyData() and destinationModel.GetPolyData().GetPoints():
      with slicer.util.NodeModify(destinationModel):
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

  def onDerivedControlPointsModified(self, derivedMarkupNode, eventId=None, node=None):
    if self.updatingFromMasterMarkup or self.updatingFromDerivedMarkup:
      return

    self.updatingFromDerivedMarkup = True
    origMarkup = derivedMarkupNode.GetNodeReference("OrigMarkup")
    origModel = self.parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
    nodeType = derivedMarkupNode.GetAttribute("NeuroSegmentParcellation.NodeType")
    locator = None
    derivedModelNode = None
    otherMarkupNode = None
    otherModelNode = None
    if nodeType == self.PIAL_NODE_ATTRIBUTE_VALUE:
      locator = self.pialPointLocator
      derivedModelNode = self.parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)

      otherMarkupNode = self.getDerivedControlPointsNode(origMarkup, self.INFLATED_NODE_ATTRIBUTE_VALUE)
      otherModelNode = self.parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)
    elif nodeType == self.INFLATED_NODE_ATTRIBUTE_VALUE:
      locator = self.inflatedPointLocator
      derivedModelNode = self.parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)

      otherMarkupNode = self.getDerivedControlPointsNode(origMarkup, self.PIAL_NODE_ATTRIBUTE_VALUE)
      otherModelNode = self.parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)
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

    # TODO: We should be able to reverse engineer where this point should be inserted to be added to the self.ORIG_NODE_ATTRIBUTE_VALUE curve
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
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
    try:
      with slicer.util.NodeModify(parameterNode):
        astNode = ast.parse(queryString)
        eq = NeuroSegmentParcellationVisitor(self)
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
    return [success, errorMessage]

  def exportOutputToSegmentation(self, parameterNode, surfacesToExport=[]):
    if parameterNode is None:
      return

    exportSegmentationNode = self.getExportSegmentation()
    if exportSegmentationNode is None:
      logging.error("exportOutputToSegmentation: Invalid segmentation node")
      return

    origModelNode = self.getOrigModelNode()
    if origModelNode is None:
      logging.error("exportOutputToSegmentation: Invalid orig node")
      return

    pialModelNode = self.getPialModelNode()
    if pialModelNode is None:
      logging.error("exportOutputToSegmentation: Invalid pial node")
      return

    with slicer.util.NodeModify(exportSegmentationNode):
      for outputModelNode in self.getOutputModelNodes():
        if len(surfacesToExport) > 0 and not outputModelNode.GetName() in surfacesToExport:
          continue
        self.exportMeshToSegmentation(outputModelNode, origModelNode, pialModelNode, exportSegmentationNode)
      exportSegmentationNode.CreateDefaultDisplayNodes()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onMarkupLockStateModified(self, markupNode, eventId=None, callData=None):
    """
    Function that is called when the lock state of the master markup node is changed.
    Applies the same lock state to all of the derived nodes.
    """
    if self.updatingFromMasterMarkup or markupNode is None:
      return

    nodeType = markupNode.GetAttribute("NeuroSegmentParcellation.NodeType")
    if nodeType is None or nodeType == "":
      return

    if nodeType != self.ORIG_NODE_ATTRIBUTE_VALUE:
      return

    wasUpdatingFromMasterMarkup = self.updatingFromMasterMarkup
    self.updatingFromMasterMarkup = True

    pialControlPoints = self.getDerivedControlPointsNode(markupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
    if pialControlPoints:
      pialControlPoints.SetLocked(markupNode.GetLocked())
    inflatedControlPoints = self.getDerivedControlPointsNode(markupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
    if inflatedControlPoints:
      inflatedControlPoints.SetLocked(markupNode.GetLocked())

    self.updatingFromMasterMarkup = wasUpdatingFromMasterMarkup

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onMasterMarkupDisplayModified(self, markupNode, eventId=None, callData=None):
    """
    Function that is called when the lock state of the master markup node is changed.
    Applies the same lock state to all of the derived nodes.
    """
    if self.updatingFromMasterMarkup or markupNode is None or markupNode.GetDisplayNode() is None:
      return

    nodeType = markupNode.GetAttribute("NeuroSegmentParcellation.NodeType")
    if nodeType is None or nodeType == "":
      return

    if nodeType != self.ORIG_NODE_ATTRIBUTE_VALUE:
      return

    wasUpdatingFromMasterMarkup = self.updatingFromMasterMarkup
    self.updatingFromMasterMarkup = True

    derivedNodes = [
      self.getDerivedControlPointsNode(markupNode, self.PIAL_NODE_ATTRIBUTE_VALUE),
      self.getDerivedCurveNode(markupNode,         self.PIAL_NODE_ATTRIBUTE_VALUE),
      self.getDerivedControlPointsNode(markupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE),
      self.getDerivedCurveNode(markupNode,         self.INFLATED_NODE_ATTRIBUTE_VALUE),
    ]

    for derivedNode in derivedNodes:
      if derivedNode is None:
        continue
      displayNode = derivedNode.GetDisplayNode()
      if displayNode is None:
        derivedNode.CreateDefaultDisplayNodes()
        displayNode = derivedNode.GetDisplayNode()
      if displayNode is None:
        continue
      displayNode.CopyContent(markupNode.GetDisplayNode())

    self.updatingFromMasterMarkup = wasUpdatingFromMasterMarkup

  def getQueryNode(self):
    if self.parameterNode is None:
      return None
    return self.parameterNode.GetNodeReference(self.INPUT_QUERY_REFERENCE)

  def setQueryNode(self, queryNode):
    if self.parameterNode is None:
      return None
    id = None
    if queryNode:
      id = queryNode.GetID()
    self.parameterNode.SetNodeReferenceID(self.INPUT_QUERY_REFERENCE, id)

  def getExportSegmentation(self):
    """
    TODO
    """
    if self.parameterNode is None:
      return None
    return self.parameterNode.GetNodeReference(self.EXPORT_SEGMENTATION_REFERENCE)

  def setExportSegmentation(self, segmentationNode):
    if self.parameterNode is None:
      return
    id = None
    if segmentationNode:
      id = segmentationNode.GetID()
    self.parameterNode.SetNodeReferenceID(self.EXPORT_SEGMENTATION_REFERENCE, id)

  def getOrigModelNode(self):
    """
    TODO
    """
    if self.parameterNode is None:
      return None
    return self.parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)

  def setOrigModelNode(self, modelNode):
    if self.parameterNode is None:
      return
    id = None
    if modelNode:
      id = modelNode.GetID()
    self.parameterNode.SetNodeReferenceID(self.ORIG_MODEL_REFERENCE, id)

  def getPialModelNode(self):
    """
    TODO
    """
    if self.parameterNode is None:
      return None
    return self.parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)

  def setPialModelNode(self, modelNode):
    if self.parameterNode is None:
      return
    id = None
    if modelNode:
      id = modelNode.GetID()
    self.parameterNode.SetNodeReferenceID(self.PIAL_MODEL_REFERENCE, id)

  def getInflatedModelNode(self):
    """
    TODO
    """
    if self.parameterNode is None:
      return None
    return self.parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)

  def setInflatedModelNode(self, modelNode):
    if self.parameterNode is None:
      return
    id = None
    if modelNode:
      id = modelNode.GetID()
    self.parameterNode.SetNodeReferenceID(self.INFLATED_MODEL_REFERENCE, id)

  def getNumberOfOutputModels(self):
    if self.parameterNode is None:
      return 0
    return self.parameterNode.GetNumberOfNodeReferences(self.OUTPUT_MODEL_REFERENCE)

  def getToolNodes(self):
    if self.parameterNode is None:
      return []

    toolNodes = []
    numberOfToolNodes = self.parameterNode.GetNumberOfNodeReferences(self.TOOL_NODE_REFERENCE)
    for i in range(numberOfToolNodes):
      toolNode = self.parameterNode.GetNthNodeReference(self.TOOL_NODE_REFERENCE, i)
      toolNodes.append(toolNode)
    return toolNodes

  def getInputMarkupNodes(self):
    if self.parameterNode is None:
      return []

    inputMarkupNodes = []
    numberOfInputMarkupNodes = self.parameterNode.GetNumberOfNodeReferences(self.INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfInputMarkupNodes):
      inputMarkupNode = self.parameterNode.GetNthNodeReference(self.INPUT_MARKUPS_REFERENCE, i)
      inputMarkupNodes.append(inputMarkupNode)
    return inputMarkupNodes

  def getOutputModelNodes(self):
    if self.parameterNode is None:
      return []

    outputModelNodes = []
    numberOfOutputModelNodes = self.parameterNode.GetNumberOfNodeReferences(self.OUTPUT_MODEL_REFERENCE)
    for i in range(numberOfOutputModelNodes):
      outputModelNode = self.parameterNode.GetNthNodeReference(self.OUTPUT_MODEL_REFERENCE, i)
      outputModelNodes.append(outputModelNode)
    return outputModelNodes

  def getInputSeedNode(self, toolNode):
    if toolNode is None:
      return
    return toolNode.GetNodeReference(self.BOUNDARY_CUT_INPUT_SEED_REFERENCE)

  def setToolNodesContinuousUpdate(self, continuousUpdate):
    for toolNode in self.getToolNodes():
      toolNode.SetContinuousUpdate(continuousUpdate)

  def setScalarOverlay(self, scalarName):
    if scalarName is None:
      return

    colorNode = None
    attributeType = 0
    if scalarName == "curv":
      attributeType = vtk.vtkDataObject.POINT
      colorNode = slicer.util.getNode("RedGreen")
    elif scalarName == "sulc":
      attributeType = vtk.vtkDataObject.POINT
      colorNode = slicer.util.getNode("RedGreen")
    elif scalarName == "labels":
      attributeType = vtk.vtkDataObject.CELL
      self.updateParcellationColorNode()
      colorNode = self.getParcellationColorNode()
    if colorNode is None:
      return

    modelNodes = [
      self.getOrigModelNode(),
      self.getPialModelNode(),
      self.getInflatedModelNode()
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
      displayNode.SetScalarVisibility(True)

  def setMarkupSliceViewVisibility(self, parameterNode, markupType, visible):
    if markupType != self.ORIG_NODE_ATTRIBUTE_VALUE and markupType != self.PIAL_NODE_ATTRIBUTE_VALUE and markupType != self.INFLATED_NODE_ATTRIBUTE_VALUE:
      logging.error("setMarkupSliceViewVisibility: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return
    if parameterNode is None:
      logging.error("setMarkupSliceViewVisibility: Invalid parameter node")
      return

    parameterNode.SetParameter("MarkupSliceVisibility." + markupType, "TRUE" if visible else "FALSE")

  def getMarkupSliceViewVisibility(self, parameterNode, markupType):
    if markupType != self.ORIG_NODE_ATTRIBUTE_VALUE and markupType != self.PIAL_NODE_ATTRIBUTE_VALUE and markupType != self.INFLATED_NODE_ATTRIBUTE_VALUE:
      logging.error("getMarkupSliceViewVisibility: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return False
    if parameterNode is None:
      logging.error("getMarkupSliceViewVisibility: Invalid parameter node")
      return False

    return True if parameterNode.GetParameter("MarkupSliceVisibility." + markupType) == "TRUE" else False

  def getMarkupViewIDs(self, parameterNode, markupType):
    if markupType != self.ORIG_NODE_ATTRIBUTE_VALUE and markupType != self.PIAL_NODE_ATTRIBUTE_VALUE and markupType != self.INFLATED_NODE_ATTRIBUTE_VALUE:
      logging.error("getMarkupViewIDs: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return []
    if parameterNode is None:
      logging.error("getMarkupViewIDs: Invalid parameter node")
      return []

    viewIDs = ["vtkMRMLViewNode1"]
    if self.getMarkupSliceViewVisibility(parameterNode, markupType):
      viewIDs += ["vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow"]

    if markupType == self.ORIG_NODE_ATTRIBUTE_VALUE:
      viewIDs.append("vtkMRMLViewNodeO")
    elif markupType == self.PIAL_NODE_ATTRIBUTE_VALUE:
      viewIDs.append("vtkMRMLViewNodeP")
    elif markupType == self.INFLATED_NODE_ATTRIBUTE_VALUE:
      viewIDs.append("vtkMRMLViewNodeI")
    return viewIDs

  def setMarkupProjectionEnabled(self, parameterNode, visible):
    if parameterNode is None:
      logging.error("setMarkupProjectionEnabled: Invalid parameter node")
      return

    parameterNode.SetParameter("MarkupProjectionVisibility", "TRUE" if visible else "FALSE")

  def getMarkupProjectionEnabled(self, parameterNode):
    if parameterNode is None:
      logging.error("setMarkupProjectionEnabled: Invalid parameter node")
      return False
    return True if parameterNode.GetParameter("MarkupProjectionVisibility") == "TRUE" else False

  def runDynamicModelerTool(self, toolNode):
    if toolNode is None:
      logging.error("runDynamicModelerTool: Invalid tool node")
      return

    seedNode = self.getInputSeedNode(toolNode)
    if seedNode:
      self.updateRelativeSeedNode(seedNode)

    dynamicModelerLogic = slicer.modules.dynamicmodeler.logic()
    numberOfInputMarkups = toolNode.GetNumberOfNodeReferences(self.BOUNDARY_CUT_INPUT_BORDER_REFERENCE)
    toolHasAllInputs = True
    for inputNodeIndex in range(numberOfInputMarkups):
      inputNode = toolNode.GetNthNodeReference(self.BOUNDARY_CUT_INPUT_BORDER_REFERENCE, inputNodeIndex)
      if inputNode is None:
        continue
      if inputNode.GetNumberOfControlPoints() == 0:
        toolHasAllInputs = False
        break
    if toolHasAllInputs:
      dynamicModelerLogic.RunDynamicModelerTool(toolNode)
    else:
      outputModel = toolNode.GetNodeReference(self.BOUNDARY_CUT_OUTPUT_MODEL_REFERENCE)
      if outputModel and outputModel.GetPolyData():
        outputModel.GetPolyData().Initialize()

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

  def loadQuery(self):
    if self.parameterNode is None:
      logging.error("loadQuery: Invalid parameter node")
      return False

    parcellationQueryNode = self.getQueryNode()
    if parcellationQueryNode is None:
      parcellationQueryNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode", "ParcellationQuery")
      self.setQueryNode(parcellationQueryNode)

    storageNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextStorageNode")
    storageNode.SetFileName(self.queryNodeFileName)
    storageNode.ReadData(parcellationQueryNode)
    slicer.mrmlScene.RemoveNode(storageNode)

    self.parameterNode.RemoveNodeReferenceIDs(self.INPUT_MARKUPS_REFERENCE)
    self.parameterNode.RemoveNodeReferenceIDs(self.OUTPUT_MODEL_REFERENCE)
    return self.parseParcellationString(self.parameterNode)

  def initializePedigreeIds(self, parameterNode):
    """
    Add Pedigree Ids to Orig model cell data and point data
    """
    if parameterNode is None:
      logging.error("initializePedigreeIds: Invalid parameter node")
      return

    origModelNode = parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
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
    origSurfaceNode = parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
    pialSurfaceNode = parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)
    inflatedSurfaceNode = parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)
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

    numberOfOutputModels = parameterNode.GetNumberOfNodeReferences(self.OUTPUT_MODEL_REFERENCE)
    for modelIndex in range(numberOfOutputModels):
      outputSurfaceNode = parameterNode.GetNthNodeReference(self.OUTPUT_MODEL_REFERENCE, modelIndex)
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
    self.updateParcellationColorNode()

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
    return parcellationColorNode

  def updateParcellationColorNode(self):
    parcellationColorNode = self.getParcellationColorNode()
    numberOfOutputModels = self.parameterNode.GetNumberOfNodeReferences(self.OUTPUT_MODEL_REFERENCE)
    lookupTable = vtk.vtkLookupTable()
    lookupTable.SetNumberOfColors(numberOfOutputModels + 1)
    lookupTable.SetTableValue(0, 0.1, 0.1, 0.1)
    labelValue = 1
    for i in range(numberOfOutputModels):
      outputSurfaceNode = self.parameterNode.GetNthNodeReference(self.OUTPUT_MODEL_REFERENCE, i)
      color = outputSurfaceNode.GetDisplayNode().GetColor()
      lookupTable.SetTableValue(labelValue, color[0], color[1], color[2])
      labelValue += 1
    parcellationColorNode.SetLookupTable(lookupTable)

  def getQueryString(self, parameterNode):
    if parameterNode is None:
      return None
    queryTextNode = parameterNode.GetNodeReference(self.INPUT_QUERY_REFERENCE)
    if queryTextNode is None:
      return None
    return queryTextNode.GetText()

  def addRelativeSeed(self, seedNode, relativeNode, relativeRole):
    """
    TODO
    """
    if seedNode is None:
      logging.error("addRelativeSeed: Invalid seed node")
      return
    if relativeNode is None:
      logging.error("addRelativeSeed: Invalid relative node")
      return

    seedRelativeRole = self.RELATIVE_NODE_REFERENCE + "." + relativeRole
    seedNode.AddNodeReferenceID(seedRelativeRole, relativeNode.GetID())

    relativeNode.AddNodeReferenceID(self.RELATIVE_NODE_REFERENCE, seedNode.GetID())

  def getRelativeSeedNodes(self, relativeNode):
    """
    TODO
    """
    if relativeNode is None:
      logging.error("getRelativeSeedNodes: Invalid relative node")
      return []

    seedNodes = []
    numberOfSeedNodes = relativeNode.GetNumberOfNodeReferences(self.RELATIVE_NODE_REFERENCE)
    for i in range(numberOfSeedNodes):
      seedNode = relativeNode.GetNthNodeReference(self.RELATIVE_NODE_REFERENCE, i)
      seedNodes.append(seedNode)
    return seedNodes

  def getRelativeNodesOfRole(self, seedNode, relativeRole):
    if seedNode is None:
      logging.error("getRelativeNodesOfRole: Invalid seed node")
      return []

    relativeNodes = []
    referenceRole = self.RELATIVE_NODE_REFERENCE + "." + relativeRole
    numberOfRelativeNodes = seedNode.GetNumberOfNodeReferences(referenceRole)
    for i in range(numberOfRelativeNodes):
      relativeNodes.append(seedNode.GetNthNodeReference(referenceRole, i))
    return relativeNodes

  def updateRelativeSeedNode(self, seedNode):
    """
    """
    if seedNode.GetAttribute("ManuallyPlaced") == "TRUE":
      return

    wasUpdatingSeedNodes = self.updatingSeedNodes
    self.updatingSeedNodes = True
    if seedNode.GetNumberOfControlPoints() == 0:
      self.initializeSeedNode(seedNode)
    for relativeRole in self.RELATIVE_SEED_ROLES:
      relativeNodes = self.getRelativeNodesOfRole(seedNode, relativeRole)
      for relativeNode in relativeNodes:
        self.updateRelativeSeedPosition(seedNode, relativeNode, relativeRole)
    self.snapSeedsToSurface(seedNode)
    self.updatingSeedNodes = wasUpdatingSeedNodes

  def initializeSeedNode(self, seedNode):
    seedPoint = [0.0, 0.0, 0.0]
    relativeNodes = []
    for relativeRole in self.RELATIVE_SEED_ROLES:
      relativeNodes += self.getRelativeNodesOfRole(seedNode, relativeRole)

    numberOfRelativeNodes = len(relativeNodes)
    inverseNumberOfRelativeNodes = 1.0 / numberOfRelativeNodes
    for relativeNode in relativeNodes:
      numberOfPoints = relativeNode.GetNumberOfControlPoints()
      if numberOfPoints == 0:
        continue
      averagePoint = [0,0,0]
      inverseNumberOfPoints = 1.0 / numberOfPoints
      for i in range(numberOfPoints):
        point = [0,0,0]
        relativeNode.GetNthControlPointPosition(i, point)
        vtk.vtkMath.MultiplyScalar(point, inverseNumberOfPoints)
        vtk.vtkMath.Add(point, averagePoint, averagePoint)
      vtk.vtkMath.MultiplyScalar(averagePoint, inverseNumberOfRelativeNodes)
      vtk.vtkMath.Add(averagePoint, seedPoint, seedPoint)
    seedNode.AddControlPoint(vtk.vtkVector3d(seedPoint))

  def updateRelativeSeedPosition(self, seedNode, relativeNode, relativeRole):
    if relativeNode.GetNumberOfControlPoints() == 0:
      return

    if seedNode.GetNumberOfControlPoints() == 0:
      self.initializeSeedNode(seedNode)

    for i in range(seedNode.GetNumberOfControlPoints()):
      seedPoint = [0.0, 0.0, 0.0]
      seedNode.GetNthControlPointPosition(i, seedPoint)

      closestPoint = [0.0, 0.0, 0.0]
      if relativeNode.IsA("vtkMRMLMarkupsCurveNode"):
        self.getClosestPointOnCurveAlongLine(seedPoint, relativeNode, relativeRole, closestPoint)
      elif relativeNode.IsA("vtkMRMLMarkupsPlaneNode"):
        relativeNode.GetClosestPointOnPlaneWorld(seedPoint, closestPoint)

      differenceVector = [0.0, 0.0, 0.0]
      vtk.vtkMath.Subtract(seedPoint, closestPoint, differenceVector)

      invalidAxis = -1
      if relativeRole == self.LATERAL_OF_RELATIVE_ROLE and abs(seedPoint[0]) < abs(closestPoint[0]):
        invalidAxis = 0
      elif relativeRole == self.MEDIAL_OF_RELATIVE_ROLE and abs(seedPoint[0]) > abs(closestPoint[0]):
        invalidAxis = 0
      if relativeRole == self.ANTERIOR_OF_RELATIVE_ROLE and differenceVector[1] < 0.0:
        invalidAxis = 1
      elif relativeRole == self.POSTERIOR_OF_RELATIVE_ROLE and differenceVector[1] > 0.0:
        invalidAxis = 1
      elif relativeRole == self.SUPERIOR_OF_RELATIVE_ROLE and differenceVector[2] < 0.0:
        invalidAxis = 2
      elif relativeRole == self.INFERIOR_OF_RELATIVE_ROLE and differenceVector[2] > 0.0:
        invalidAxis = 2
      if invalidAxis < 0:
        continue

      seedPoint[invalidAxis] = closestPoint[invalidAxis] - (differenceVector[invalidAxis])
      seedNode.SetNthControlPointPosition(i, seedPoint[0], seedPoint[1], seedPoint[2])

  def getClosestPointOnCurveAlongLine(self, seedPoint, curveNode, relativeRole, closestPoint):
    minimumDistance = vtk.VTK_DOUBLE_MAX
    curvePoints = curveNode.GetCurve().GetPoints()

    lateralDirection = [1, 0, 0]
    medialDirection = [-1, 0, 0]
    if seedPoint[0] < 0.0:
      lateralDirection[0] = -1.0
      medialDirection[0] = 1.0
    anteriorDirection = [0, 1, 0]
    posteriorDirection = [0, -1, 0]
    superiorDirection = [0, 0, 1]
    inferiorDirection = [0, 0, -1]

    directionVector = [0,0,0]
    if relativeRole == self.LATERAL_OF_RELATIVE_ROLE:
      directionVector = medialDirection
    elif relativeRole == self.MEDIAL_OF_RELATIVE_ROLE:
      directionVector = lateralDirection
    elif relativeRole == self.ANTERIOR_OF_RELATIVE_ROLE:
      directionVector = posteriorDirection
    elif relativeRole == self.POSTERIOR_OF_RELATIVE_ROLE:
      directionVector = anteriorDirection
    elif relativeRole == self.SUPERIOR_OF_RELATIVE_ROLE:
      directionVector = inferiorDirection
    elif relativeRole == self.INFERIOR_OF_RELATIVE_ROLE:
      directionVector = superiorDirection
    else:
      logging.error("getClosestPointOnCurveAlongLine: Invalid relative role")
      return

    seedLineEnd = directionVector[:]
    vtk.vtkMath.MultiplyScalar(seedLineEnd, 10000)
    vtk.vtkMath.Add(seedPoint, seedLineEnd, seedLineEnd)

    t = 0
    pointOnLine = [0,0,0]    
    for i in range(curvePoints.GetNumberOfPoints()):
      curvePoint = curvePoints.GetPoint(i)     
      distance = vtk.vtkLine.DistanceToLine(curvePoint, seedPoint, seedLineEnd, vtk.reference(t), pointOnLine)
      if distance < minimumDistance:
        minimumDistance = distance
        closestPoint[0] = pointOnLine[0]
        closestPoint[1] = pointOnLine[1]
        closestPoint[2] = pointOnLine[2]
