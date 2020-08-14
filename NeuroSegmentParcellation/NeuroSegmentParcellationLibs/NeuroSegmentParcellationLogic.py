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


  INPUT_MARKUPS_REFERENCE = "InputMarkups"
  ORIG_MODEL_REFERENCE = "OrigModel"
  PIAL_MODEL_REFERENCE = "PialModel"
  INFLATED_MODEL_REFERENCE = "InflatedModel"
  INPUT_QUERY_REFERENCE = "InputQuery"
  OUTPUT_MODEL_REFERENCE = "OutputModel"
  TOOL_NODE_REFERENCE = "ToolNode"
  EXPORT_SEGMENTATION_REFERENCE = "ExportSegmentation"

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

    self.updateInputMarkupObservers(parameterNode)
    self.updateAllModelViews(parameterNode)
    self.updatePointLocators(parameterNode)

    origModelNode = parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
    numberOfToolNodes = parameterNode.GetNumberOfNodeReferences(self.TOOL_NODE_REFERENCE)
    for i in range(numberOfToolNodes):
      toolNode = parameterNode.GetNthNodeReference(self.TOOL_NODE_REFERENCE, i)
      if origModelNode is None:
        toolNode.RemoveNodeReferenceIDs("BoundaryCut.InputModel")
      elif toolNode.GetNodeReference("BoundaryCut.InputModel") != origModelNode:
        toolNode.SetNodeReferenceID("BoundaryCut.InputModel", origModelNode.GetID())

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

  def updatePointLocators(self, parameterNode):
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
    self.removeInputMarkupObservers()
    if parameterNode is None:
      return

    origMarkupViews = self.getMarkupViewIDs(parameterNode, "orig")
    pialMarkupViews = self.getMarkupViewIDs(parameterNode, "pial")
    inflatedMarkupViews = self.getMarkupViewIDs(parameterNode, "inflated")

    numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(self.INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfMarkupNodes):
      inputMarkupNode = parameterNode.GetNthNodeReference(self.INPUT_MARKUPS_REFERENCE, i)
      if not inputMarkupNode.IsA("vtkMRMLMarkupsCurveNode"):
        continue
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onMasterMarkupModified)
      self.inputMarkupObservers.append((inputMarkupNode, tag))
      inputMarkupNode.GetDisplayNode().SetViewNodeIDs(origMarkupViews)
      inputMarkupNode.SetAttribute("NeuroSegmentParcellation.NodeType", "Orig")

      pialControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, "Pial")
      if pialControlPoints:
        tag = pialControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((pialControlPoints, tag))
        tag = pialControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((pialControlPoints, tag))
        pialControlPoints.GetDisplayNode().SetViewNodeIDs(pialMarkupViews)

      inflatedControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, "Inflated")
      if inflatedControlPoints:
        tag = inflatedControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((inflatedControlPoints, tag))
        tag = inflatedControlPoints.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onDerivedControlPointsModified)
        self.inputMarkupObservers.append((inflatedControlPoints, tag))
        inflatedControlPoints.GetDisplayNode().SetViewNodeIDs(inflatedMarkupViews)

      pialCurveNode = self.getDerivedCurveNode(inputMarkupNode, "Pial")
      if pialCurveNode:
        pialCurveNode.GetDisplayNode().SetViewNodeIDs(pialMarkupViews)

      inflatedCurveNode = self.getDerivedCurveNode(inputMarkupNode, "Inflated")
      if inflatedCurveNode:
        inflatedCurveNode.GetDisplayNode().SetViewNodeIDs(inflatedMarkupViews)

      numberOfToolNodes = parameterNode.GetNumberOfNodeReferences(self.TOOL_NODE_REFERENCE)
      for i in range(numberOfToolNodes):
        toolNode = parameterNode.GetNthNodeReference(self.TOOL_NODE_REFERENCE, i)
        inputSeed = toolNode.GetNodeReference(self.BOUNDARY_CUT_INPUT_SEED_REFERENCE)
        if inputSeed:
          inputSeed.GetDisplayNode().SetViewNodeIDs(["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow", "vtkMRMLViewNodeO"])

  def onMasterMarkupModified(self, inputMarkupNode, eventId=None, node=None):
    if self.updatingFromMasterMarkup or self.parameterNode is None:
      return

    origModel = self.parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)
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

    inflatedMarkup = self.getDerivedCurveNode(inputMarkupNode, "Inflated")
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
    if nodeType == "Pial":
      locator = self.pialPointLocator
      derivedModelNode = self.parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)

      otherMarkupNode = self.getDerivedControlPointsNode(origMarkup, "Inflated")
      otherModelNode = self.parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)
    elif nodeType == "Inflated":
      locator = self.inflatedPointLocator
      derivedModelNode = self.parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)

      otherMarkupNode = self.getDerivedControlPointsNode(origMarkup, "Pial")
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
    if markupType != "orig" and markupType != "pial" and markupType != "inflated":
      logging.error("setMarkupSliceViewVisibility: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return
    if parameterNode is None:
      logging.error("setMarkupSliceViewVisibility: Invalid parameter node")
      return False

    parameterNode.SetParameter("MarkupSliceVisibility." + markupType, "TRUE" if visible else "FALSE")

  def getMarkupSliceViewVisibility(self, parameterNode, markupType):
    if markupType != "orig" and markupType != "pial" and markupType != "inflated":
      logging.error("getMarkupSliceViewVisibility: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return
    if parameterNode is None:
      logging.error("getMarkupSliceViewVisibility: Invalid parameter node")
      return False

    return True if parameterNode.GetParameter("MarkupSliceVisibility." + markupType) == "TRUE" else False

  def getMarkupViewIDs(self, parameterNode, markupType):
    if markupType != "orig" and markupType != "pial" and markupType != "inflated":
      logging.error("getMarkupViewIDs: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return []
    if parameterNode is None:
      logging.error("getMarkupViewIDs: Invalid parameter node")
      return []

    viewIDs = ["vtkMRMLViewNode1"]
    if self.getMarkupSliceViewVisibility(parameterNode, markupType):
      viewIDs += ["vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow"]

    if markupType == "orig":
      viewIDs.append("vtkMRMLViewNodeO")
    elif markupType == "pial":
      viewIDs.append("vtkMRMLViewNodeP")
    elif markupType == "inflated":
      viewIDs.append("vtkMRMLViewNodeI")
    return viewIDs

  def runDynamicModelerTool(self, toolNode):
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
