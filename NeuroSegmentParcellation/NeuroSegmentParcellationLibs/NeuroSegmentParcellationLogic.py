import os
import ast
import vtk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging
import json

from NeuroSegmentParcellationLibs.NeuroSegmentParcellationVisitor import NeuroSegmentParcellationVisitor
from NeuroSegmentParcellationLibs.NeuroSegmentMarkupsIntersectionDisplayManager import NeuroSegmentMarkupsIntersectionDisplayManager

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
  INTERSECTION_MODEL_REFERENCE = "PlaneIntersection"
  LABEL_OUTLINE_MODEL_REFERENCE = "LabelOutline"

  ORIG_NODE_ATTRIBUTE_VALUE = "Orig"
  PIAL_NODE_ATTRIBUTE_VALUE = "Pial"
  INFLATED_NODE_ATTRIBUTE_VALUE = "Inflated"
  NODE_TYPES = [
    ORIG_NODE_ATTRIBUTE_VALUE,
    PIAL_NODE_ATTRIBUTE_VALUE,
    INFLATED_NODE_ATTRIBUTE_VALUE,
  ]

  NODE_TYPE_ATTRIBUTE_NAME = "NeuroSegmentParcellation.NodeType"
  MANUALLY_PLACED_ATTRIBUTE_NAME = "NeuroSegmentParcellation.ManuallyPlaced"
  MARKUP_SLICE_VISIBILITY_PARAMETER_PREFIX = "MarkupSliceVisibility."
  NEUROSEGMENT_OUTPUT_ATTRIBUTE_VALUE = "NeuroSegmentParcellation.Output"
  PARCELLATION_ROLE_ATTRIBUTE = "NeuroSegmentParcellation.Role"

  CURVE_VISIBILITY_RED_VIEW = "CurveVisibilityRedView"
  CURVE_VISIBILITY_GREEN_VIEW = "CurveVisibilityGreenView"
  CURVE_VISIBILITY_YELLOW_VIEW = "CurveVisibilityYellowView"

  INTERSECTION_VISIBILITY_RED_VIEW = "IntersectionVisibilityRedView"
  INTERSECTION_VISIBILITY_GREEN_VIEW = "IntersectionVisibilityGreenView"
  INTERSECTION_VISIBILITY_YELLOW_VIEW = "IntersectionVisibilityYellowView"

  LABEL_TEXT_VISIBILITY = "LabelTextVisibility"

  PLANE_INTERSECTION_VISIBILITY_NAME = "PlaneIntersectionVisibility"

  CURVE_INTERSECTION_GLYPH_TYPE_NAME = "CurveIntersectionGlyphType"
  CURVE_INTERSECTION_GLYPH_SCALE_NAME = "CurveIntersectionGlyphScale"

  LABEL_OUTLINE_VISIBILITY_NAME = "LabelOutlineVisibility"

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

    try:
      slicer.intersectionDisplayManager
    except AttributeError as error:
      slicer.intersectionDisplayManager = NeuroSegmentMarkupsIntersectionDisplayManager()

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.updateParameterNodeObservers)
    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)
    scriptedModuleNodes = slicer.util.getNodesByClass("vtkMRMLScriptedModuleNode")
    for node in scriptedModuleNodes:
      if node.GetAttribute("ModuleName") == self.moduleName:
        self.setParameterNode(node)
        break
    self.updateParameterNodeObservers()

  def setParameterNode(self, parameterNode):
    """Set the current parameter node and initialize all unset parameters to their default values"""
    if self.parameterNode==parameterNode:
      return
    self.parameterNode = parameterNode
    if self.parameterNode is None:
      return
    if self.getQueryNode() is None:
      self.loadQuery(self.queryNodeFileName)
    self.updateModelNodes()
    self.onParameterNodeModified(parameterNode)

  def getParameterNode(self):
    """Returns the current parameter node and creates one if it doesn't exist yet"""
    if not self.parameterNode:
      self.setParameterNode(ScriptedLoadableModuleLogic.getParameterNode(self))
    return self.parameterNode

  def createParameterNode(self):
    parameterNode = ScriptedLoadableModuleLogic.createParameterNode(self)
    self.setDefaultParameters(parameterNode)
    return parameterNode

  def getQueryNodeFileName(self):
    return self.queryNodeFileName

  def setQueryNodeFileName(self, fileName):
    self.queryNodeFileName = fileName

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def updateParameterNodeObservers(self, caller=None, eventId=None, callData=None):
    try:
      slicer.app.pauseRender()
      scriptedModuleNodes = slicer.util.getNodesByClass("vtkMRMLScriptedModuleNode")
      for node in scriptedModuleNodes:
        if node.GetAttribute("ModuleName") == self.moduleName:
          if not self.hasObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified):
            self.addObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)
          self.onParameterNodeModified(node)
    finally:
      slicer.app.resumeRender()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, eventId, node):
    if node is None:
      return

    if node.IsA("vtkMRMLScriptedModuleNode") and node.GetAttribute("ModuleName") == self.moduleName:
      if not self.hasObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified):
        self.addObserver(node, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)

    elif node.IsA("vtkMRMLModelNode") and self.getParameterNode():
      fileTypeAttributeName = slicer.vtkMRMLFreeSurferModelStorageNode.GetFreeSurferFileTypeAttributeName()
      fileTypeAttributeValue = node.GetAttribute(fileTypeAttributeName)
      if fileTypeAttributeValue is None or fileTypeAttributeValue == "":
        return
      self.updateModelNodes()

  def updateModelNodes(self):
    parameterNode = self.getParameterNode()
    fileTypeAttributeName = slicer.vtkMRMLFreeSurferModelStorageNode.GetFreeSurferFileTypeAttributeName()
    modelNodes = slicer.util.getNodesByClass("vtkMRMLModelNode")

    origModelNode = self.getOrigModelNode(parameterNode)
    pialModelNode = self.getPialModelNode(parameterNode)
    inflatedModelNode = self.getInflatedModelNode(parameterNode)
    if origModelNode and pialModelNode and inflatedModelNode:
      return

    for modelNode in modelNodes:
      fileTypeAttributeValue = modelNode.GetAttribute(fileTypeAttributeName)

      if origModelNode is None and (fileTypeAttributeValue == ".orig" or fileTypeAttributeValue == ".white"):
        self.setOrigModelNode(parameterNode, modelNode)

      elif pialModelNode is None and fileTypeAttributeValue == ".pial":
        self.setPialModelNode(parameterNode, modelNode)

      elif inflatedModelNode is None and fileTypeAttributeValue == ".inflated":
        self.setInflatedModelNode(parameterNode, modelNode)

  def onParameterNodeModified(self, parameterNode, eventId=None):
    if parameterNode is None or slicer.mrmlScene.IsImporting():
      return

    try:
      slicer.app.pauseRender()
      self.updateInputModelNodes(parameterNode)
      self.updateInputModelPointLocators(parameterNode)
      self.updateAllModelViews(parameterNode)

      self.removeInputMarkupObservers()
      self.updatePlaneIntersectionVisibility()
      self.updateInputMarkupDisplay(parameterNode)
      self.updateInputMarkupSurfaceCostFunction(parameterNode)
      self.updateInputMarkupObservers(parameterNode)
      self.updateOutputModelAttributes(parameterNode)
    finally:
      slicer.app.resumeRender()

  def updateOutputModelAttributes(self, parameterNode):
    for outputModelNode in self.getOutputModelNodes():
      outputModelNode.SetAttribute(self.NEUROSEGMENT_OUTPUT_ATTRIBUTE_VALUE, str(True))

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
        inputCurveNode.SetSurfaceConstraintMaximumSearchRadiusTolerance(0.0)

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
      modelNode.CreateDefaultDisplayNodes()
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
        inputMarkupNode.SetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME, self.ORIG_NODE_ATTRIBUTE_VALUE)
        self.onMarkupLockStateModified(inputMarkupNode)

      if inputMarkupNode.IsA("vtkMRMLMarkupsPlaneNode"):
        tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onPlaneNodeModified)
        self.inputMarkupObservers.append((inputMarkupNode, tag))
        tag = inputMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.DisplayModifiedEvent, self.onPlaneDisplayModified)
        self.inputMarkupObservers.append((inputMarkupNode, tag))
        inputMarkupNode.SetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME, self.ORIG_NODE_ATTRIBUTE_VALUE)

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

    slicer.intersectionDisplayManager.setGlyphType(self.getIntersectionGlyphType())
    slicer.intersectionDisplayManager.setGlyphScale(self.getIntersectionGlyphScale())

    intersectionViewIDs = []
    if self.getRedIntersectionVisibility():
      intersectionViewIDs.append("Red")
    if self.getGreenIntersectionVisibility():
      intersectionViewIDs.append("Green")
    if self.getYellowIntersectionVisibility():
      intersectionViewIDs.append("Yellow")

    labelVisibility = self.getLabelVisibility()

    numberOfMarkupNodes = parameterNode.GetNumberOfNodeReferences(self.INPUT_MARKUPS_REFERENCE)
    for i in range(numberOfMarkupNodes):
      inputMarkupNode = parameterNode.GetNthNodeReference(self.INPUT_MARKUPS_REFERENCE, i)
      inputMarkupNode.CreateDefaultDisplayNodes()
      if inputMarkupNode.IsA("vtkMRMLMarkupsPlaneNode"):
        inputMarkupNode.GetDisplayNode().SetViewNodeIDs([])
      else:
        inputMarkupNode.GetDisplayNode().SetViewNodeIDs(origMarkupViews)
      inputMarkupNode.SetAttribute(slicer.intersectionDisplayManager.INTERSECTION_VISIBLE_ATTRIBUTE, str(True))
      inputMarkupNode.SetAttribute(slicer.intersectionDisplayManager.INTERSECTION_VIEWS_ATTRIBUTE, json.dumps(intersectionViewIDs))

      if not inputMarkupNode.IsA("vtkMRMLMarkupsCurveNode"):
        continue

      pialControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
      if pialControlPoints:
        pialControlPoints.CreateDefaultDisplayNodes()
        pialControlPoints.GetDisplayNode().SetViewNodeIDs(pialMarkupViews)

      inflatedControlPoints = self.getDerivedControlPointsNode(inputMarkupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
      if inflatedControlPoints:
        inflatedControlPoints.CreateDefaultDisplayNodes()
        inflatedControlPoints.GetDisplayNode().SetViewNodeIDs(inflatedMarkupViews)

      pialCurveNode = self.getDerivedCurveNode(inputMarkupNode, self.PIAL_NODE_ATTRIBUTE_VALUE)
      if pialCurveNode:
        pialCurveNode.CreateDefaultDisplayNodes()
        pialCurveNode.GetDisplayNode().SetViewNodeIDs(pialMarkupViews)

      inflatedCurveNode = self.getDerivedCurveNode(inputMarkupNode, self.INFLATED_NODE_ATTRIBUTE_VALUE)
      if inflatedCurveNode:
        inflatedCurveNode.CreateDefaultDisplayNodes()
        inflatedCurveNode.GetDisplayNode().SetViewNodeIDs(inflatedMarkupViews)

      currentAndDerivedMarkups = [inputMarkupNode, pialControlPoints, pialCurveNode, inflatedControlPoints, inflatedCurveNode]
      for markupsNode in currentAndDerivedMarkups:
        markupsNode.GetDisplayNode().SetPropertiesLabelVisibility(labelVisibility)

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
      origPointLocal = list(curvePoints.GetPoint(i))
      origModel.TransformPointFromWorld(origPointLocal, origPointLocal)
      pointIds.append(self.origPointLocator.FindClosestPoint(origPointLocal))

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
    seedNode.SetAttribute(self.MANUALLY_PLACED_ATTRIBUTE_NAME, "TRUE")

  def onSeedRemoved(self, seedNode, eventId=None, callData=None):
    if seedNode is None:
      return
    if seedNode.GetNumberOfControlPoints() != 0:
      return
    seedNode.SetAttribute(self.MANUALLY_PLACED_ATTRIBUTE_NAME, "FALSE")

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
        destinationControlPoints_World = vtk.vtkPoints()
        destinationControlPoints_World.SetNumberOfPoints(sourceMarkup.GetNumberOfControlPoints())
        destinationMarkup.RemoveAllControlPoints()
        for i in range(sourceMarkup.GetNumberOfControlPoints()):
          if not copyUndefinedControlPoints and sourceMarkup.GetNthControlPointPositionStatus(i) != sourceMarkup.PositionDefined:
            continue
          sourcePoint = [0,0,0]
          sourceMarkup.GetNthControlPointPositionWorld(i, sourcePoint)
          sourceModel.TransformPointFromWorld(sourcePoint, sourcePoint)
          pointId = sourceLocator.FindClosestPoint(sourcePoint)
          destinationPoint_World = list(destinationModel.GetPolyData().GetPoints().GetPoint(pointId))
          destinationModel.TransformPointToWorld(destinationPoint_World, destinationPoint_World)

          destinationControlPoints_World.SetPoint(i, destinationPoint_World)
        destinationMarkup.SetControlPointPositionsWorld(destinationControlPoints_World)

  def onDerivedControlPointsModified(self, derivedMarkupNode, eventId=None, node=None):
    if self.updatingFromMasterMarkup or self.updatingFromDerivedMarkup:
      return

    try:
      slicer.app.pauseRender()

      self.updatingFromDerivedMarkup = True
      origMarkup = derivedMarkupNode.GetNodeReference("OrigMarkup")
      origModel = self.parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
      nodeType = derivedMarkupNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME)
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

    finally:
      slicer.app.resumeRender()

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
    derivedMarkup.SetName(origMarkupNode.GetName() + "_" + nodeReference)
    derivedMarkup.CreateDefaultDisplayNodes()
    derivedMarkup.UndoEnabledOff()
    derivedMarkup.SetLocked(True)
    derivedMarkup.GetDisplayNode().CopyContent(origMarkupNode.GetDisplayNode())
    if derivedMarkup.IsA("vtkMRMLMarkupsCurveNode"):
      derivedMarkup.SetCurveTypeToLinear()
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
    derivedMarkup.SetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME, nodeType)
    origMarkupNode.SetNodeReferenceID(nodeReference, derivedMarkup.GetID())
    derivedMarkup.SetNodeReferenceID("OrigMarkup", origMarkupNode.GetID())

    return derivedMarkup

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if parameterNode is None:
      return

    parameterNode.SetParameter(self.CURVE_VISIBILITY_RED_VIEW, "TRUE")
    parameterNode.SetParameter(self.CURVE_VISIBILITY_GREEN_VIEW, "FALSE")
    parameterNode.SetParameter(self.CURVE_VISIBILITY_YELLOW_VIEW, "TRUE")

    parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_RED_VIEW, "FALSE")
    parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_GREEN_VIEW, "TRUE")
    parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_YELLOW_VIEW, "FALSE")

    parameterNode.SetParameter(self.MARKUP_SLICE_VISIBILITY_PARAMETER_PREFIX + self.ORIG_NODE_ATTRIBUTE_VALUE, "TRUE")
    parameterNode.SetParameter(self.MARKUP_SLICE_VISIBILITY_PARAMETER_PREFIX + self.PIAL_NODE_ATTRIBUTE_VALUE, "FALSE")
    parameterNode.SetParameter(self.MARKUP_SLICE_VISIBILITY_PARAMETER_PREFIX + self.INFLATED_NODE_ATTRIBUTE_VALUE, "FALSE")

  def parseParcellationString(self, parameterNode):
    queryString = self.getQueryString(parameterNode)
    if queryString is None:
      logging.error("Invalid query!")
      return

    success = False
    errorMessage = ""
    try:
      slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
      slicer.app.pauseRender()

      logging.debug("Attempting to parse parcellation string:\n_________________\n{0}\n_________________".format(queryString))

      with slicer.util.NodeModify(parameterNode):
        astNode = ast.parse(queryString)
        eq = NeuroSegmentParcellationVisitor(self)
        eq.setParameterNode(parameterNode)
        parameterNode.RemoveNodeReferenceIDs(self.INPUT_MARKUPS_REFERENCE)
        parameterNode.RemoveNodeReferenceIDs(self.OUTPUT_MODEL_REFERENCE)
        parameterNode.RemoveNodeReferenceIDs(self.TOOL_NODE_REFERENCE)
        eq.visit(astNode)
        success = True

    except Exception as e:
      slicer.util.errorDisplay("Error parsing parcellation: "+str(e))
      import traceback
      traceback.print_exc()
      logging.error("Error parsing mesh tool string!")
    finally:
      slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)
      slicer.app.resumeRender()
    return [success, errorMessage]

  def exportOutputToSegmentation(self, parameterNode, surfacesToExport=[]):
    """
    Export the contents of the specified surfaces to a segmentation
    :param parameterNode: Parameter node referencing the surfaces to export.
    :param surfacesToExport: List of surfaces to export. If empty, all surfaces will be exported
    :return: True if successful, otherwise false
    """
    if parameterNode is None:
      return False

    exportSegmentationNode = self.getExportSegmentation()
    if exportSegmentationNode is None:
      logging.error("exportOutputToSegmentation: Invalid segmentation node")
      return False

    origModelNode = self.getOrigModelNode(parameterNode)
    if origModelNode is None:
      logging.error("exportOutputToSegmentation: Invalid orig node")
      return False

    pialModelNode = self.getPialModelNode(parameterNode)
    if pialModelNode is None:
      logging.error("exportOutputToSegmentation: Invalid pial node")
      return False

    try:
      wasModifying = exportSegmentationNode.StartModify()
      slicer.app.pauseRender()

      self.updateLabelOverlay()
      outputModelNodes = self.getOutputModelNodes()

      outputOrigPolyData = vtk.vtkPolyData()
      tempModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
      tempModelNode.SetAndObservePolyData(outputOrigPolyData)
      tempModelNode.CreateDefaultDisplayNodes()

      if origModelNode.GetParentTransformNode():
        tempModelNode.SetAndObserveTransformNodeID(origModelNode.GetParentTransformNode().GetID())
      for i in range(self.getNumberOfOutputModels()):
        outputModelNode = outputModelNodes[i]
        if len(surfacesToExport) > 0 and not outputModelNode.GetName() in surfacesToExport:
          continue
        tempModelNode.GetDisplayNode().CopyContent(outputModelNode.GetDisplayNode())
        tempModelNode.SetName(outputModelNode.GetName())
        self.getOrigPolyDataForLabel(parameterNode, i+1, outputOrigPolyData)
        self.exportMeshToSegmentation(tempModelNode, origModelNode, pialModelNode, exportSegmentationNode)
        exportSegmentationNode.CreateDefaultDisplayNodes()
    finally:
      slicer.mrmlScene.RemoveNode(tempModelNode.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(tempModelNode)
      exportSegmentationNode.EndModify(wasModifying)
      slicer.app.resumeRender()

    return True

  def exportOrigSurfaceToSegmentation(self, parameterNode, surfacePatchNode, polydata):
    exportSegmentationNode = self.getExportSegmentation()
    if exportSegmentationNode is None:
      logging.error("exportOutputToSegmentation: Invalid segmentation node")
      return False
    segmentName = surfacePatchNode.GetName()
    segmentColor = surfacePatchNode.GetDisplayNode().GetColor()
    segmentation = exportSegmentationNode.GetSegmentation()
    segmentation.SetMasterRepresentationName(slicer.vtkSegmentationConverter.GetClosedSurfaceRepresentationName())
    segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)
    segment = segmentation.GetSegment(segmentId)
    segmentIndex = segmentation.GetSegmentIndex(segmentId)
    if not segment is None:
      segmentation.RemoveSegment(segment)

    cleanFilter = vtk.vtkCleanPolyData()
    cleanFilter.SetInputData(polydata)
    cleanFilter.Update()

    segment = slicer.vtkSegment()
    segment.SetName(segmentName)
    segment.SetColor(segmentColor)
    segment.AddRepresentation(slicer.vtkSegmentationConverter.GetClosedSurfaceRepresentationName(), cleanFilter.GetOutput())
    segmentation.AddSegment(segment)

  def getOrigPolyDataForLabel(self, parameterNode, labelValue, outputOrigPolyData):
    origModelNode = self.getOrigModelNode(parameterNode)
    if origModelNode is None:
      logging.error("exportOutputToSegmentation: Invalid orig node")
      return
    pialModelNode = self.getPialModelNode(parameterNode)
    if pialModelNode is None:
      logging.error("exportOutputToSegmentation: Invalid orig node")
      return

    overlayModel = origModelNode.GetPolyData()
    pointData = overlayModel.GetPointData()
    cellData = overlayModel.GetCellData()
    polys = overlayModel.GetPolys()
    labelArray = cellData.GetArray("labels")
    if labelArray is None:
      logging.error("exportOutputToSegmentation: Invalid label array")
      return

    cellIds = vtk.vtkIdList()
    for cellId in range(overlayModel.GetNumberOfPolys()):
      if labelValue != labelArray.GetValue(cellId):
        continue
      cellIds.InsertNextId(cellId)

    extractCells = vtk.vtkExtractCells()
    extractCells.SetInputData(overlayModel)
    extractCells.SetCellList(cellIds)
    geometryFilter = vtk.vtkGeometryFilter()
    geometryFilter.SetInputConnection(extractCells.GetOutputPort())
    geometryFilter.Update()
    outputOrigPolyData.DeepCopy(geometryFilter.GetOutput())

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onMarkupLockStateModified(self, markupNode, eventId=None, callData=None):
    """
    Function that is called when the lock state of the master markup node is changed.
    Applies the same lock state to all of the derived nodes.
    """
    if self.updatingFromMasterMarkup or markupNode is None:
      return

    nodeType = markupNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME)
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

    nodeType = markupNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME)
    if nodeType is None or nodeType == "":
      return

    if nodeType != self.ORIG_NODE_ATTRIBUTE_VALUE:
      return

    try:
      slicer.app.pauseRender()
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
    finally:
      slicer.app.resumeRender()

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

  def getOrigModelNode(self, parameterNode):
    """
    TODO
    """
    if parameterNode is None:
      return None
    return parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)

  def setOrigModelNode(self, parameterNode, modelNode):
    if parameterNode is None:
      return
    id = None
    if modelNode:
      id = modelNode.GetID()
    parameterNode.SetNodeReferenceID(self.ORIG_MODEL_REFERENCE, id)
    self.initializePedigreeIds(parameterNode)

  def getPialModelNode(self, parameterNode):
    """
    TODO
    """
    if parameterNode is None:
      return None
    return parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)

  def setPialModelNode(self, parameterNode, modelNode):
    if parameterNode is None:
      return
    id = None
    if modelNode:
      id = modelNode.GetID()
    parameterNode.SetNodeReferenceID(self.PIAL_MODEL_REFERENCE, id)

  def getInflatedModelNode(self, parameterNode):
    """
    TODO
    """
    if parameterNode is None:
      return None
    return parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)

  def setInflatedModelNode(self, parameterNode, modelNode):
    if parameterNode is None:
      return
    id = None
    if modelNode:
      id = modelNode.GetID()
    parameterNode.SetNodeReferenceID(self.INFLATED_MODEL_REFERENCE, id)

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

  def getPointScalarOverlays(self, modelNode):
    """
    Returns the list of point scalars in the polydata
    """
    if modelNode is None or modelNode.GetPolyData() is None:
      return []

    scalarOverlays = []
    polyData = modelNode.GetPolyData()
    pointData = polyData.GetPointData()
    for i in range(pointData.GetNumberOfArrays()):
      scalarOverlays.append(pointData.GetArray(i))
    return scalarOverlays

  def setScalarOverlay(self, parameterNode, scalarName):
    if scalarName is None:
      return

    logging.debug("setScalarOverlay: " + str(scalarName))

    colorNode = None
    attributeType = -1
    scalarMode = slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange
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
    else:
      colorNode = slicer.util.getFirstNodeByClassByName("vtkMRMLColorNode", scalarName)

    if colorNode is None:
      logging.error("setScalarOverlay: could not find color node")
      return

    modelNodes = [
      self.getOrigModelNode(parameterNode),
      self.getPialModelNode(parameterNode),
      self.getInflatedModelNode(parameterNode)
      ]
    for modelNode in modelNodes:
      if modelNode is None:
        continue
      displayNode = modelNode.GetDisplayNode()
      if displayNode is None:
        continue

      if attributeType == -1:
        displayNode.SetActiveScalarName(scalarName)
      else:
        displayNode.SetActiveScalar(scalarName, attributeType)

      if colorNode:
        displayNode.SetAndObserveColorNodeID(colorNode.GetID())
        displayNode.SetScalarRangeFlag(scalarMode)
      displayNode.SetScalarVisibility(True)

  def setMarkupSliceViewVisibility(self, parameterNode, markupType, visible):
    if markupType != self.ORIG_NODE_ATTRIBUTE_VALUE and markupType != self.PIAL_NODE_ATTRIBUTE_VALUE and markupType != self.INFLATED_NODE_ATTRIBUTE_VALUE:
      logging.error("setMarkupSliceViewVisibility: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return
    if parameterNode is None:
      logging.error("setMarkupSliceViewVisibility: Invalid parameter node")
      return

    parameterNode.SetParameter(self.MARKUP_SLICE_VISIBILITY_PARAMETER_PREFIX + markupType, "TRUE" if visible else "FALSE")

  def getMarkupSliceViewVisibility(self, parameterNode, markupType):
    if markupType != self.ORIG_NODE_ATTRIBUTE_VALUE and markupType != self.PIAL_NODE_ATTRIBUTE_VALUE and markupType != self.INFLATED_NODE_ATTRIBUTE_VALUE:
      logging.error("getMarkupSliceViewVisibility: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return False
    if parameterNode is None:
      logging.error("getMarkupSliceViewVisibility: Invalid parameter node")
      return False

    return True if parameterNode.GetParameter(self.MARKUP_SLICE_VISIBILITY_PARAMETER_PREFIX + markupType) == "TRUE" else False

  def getMarkupViewIDs(self, parameterNode, markupType):
    if markupType != self.ORIG_NODE_ATTRIBUTE_VALUE and markupType != self.PIAL_NODE_ATTRIBUTE_VALUE and markupType != self.INFLATED_NODE_ATTRIBUTE_VALUE:
      logging.error("getMarkupViewIDs: Invalid markup type. Expected orig, pial or inflated, got: " + markupType)
      return []
    if parameterNode is None:
      logging.error("getMarkupViewIDs: Invalid parameter node")
      return []

    viewIDs = ["vtkMRMLViewNode1"]
    if self.getMarkupSliceViewVisibility(parameterNode, markupType):
      if self.getRedLineVisibility():
        viewIDs += ["vtkMRMLSliceNodeRed"]
      if self.getGreenLineVisibility():
        viewIDs += ["vtkMRMLSliceNodeGreen"]
      if self.getYellowLineVisibility():
        viewIDs += ["vtkMRMLSliceNodeYellow"]

    if markupType == self.ORIG_NODE_ATTRIBUTE_VALUE:
      viewIDs.append("vtkMRMLViewNodeO")
    elif markupType == self.PIAL_NODE_ATTRIBUTE_VALUE:
      viewIDs.append("vtkMRMLViewNodeP")
    elif markupType == self.INFLATED_NODE_ATTRIBUTE_VALUE:
      viewIDs.append("vtkMRMLViewNodeI")
    return viewIDs

  def runDynamicModelerTool(self, toolNode):
    if toolNode is None:
      logging.error("runDynamicModelerTool: Invalid tool node")
      return

    seedNode = self.getInputSeedNode(toolNode)
    if seedNode:
      self.updateRelativeSeedNode(seedNode)

    self.initializePedigreeIds(self.parameterNode)

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

    outputModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", surfacePatchNode.GetName())

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
    if segment is None:
      segment = slicer.vtkSegment()
      segment.SetName(segmentName)
      segment.SetColor(segmentColor)
      segmentation.AddSegment(segment)
    segment.AddRepresentation(slicer.vtkSegmentationConverter.GetClosedSurfaceRepresentationName(), outputModelNode.GetPolyData())
    slicer.mrmlScene.RemoveNode(outputModelNode)

  def loadQuery(self, path):
    if self.parameterNode is None:
      logging.error("loadQuery: Invalid parameter node")
      return False

    parcellationQueryNode = self.getQueryNode()
    if parcellationQueryNode is None:
      parcellationQueryNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode", "ParcellationQuery")
      self.setQueryNode(parcellationQueryNode)

    storageNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextStorageNode")
    storageNode.SetFileName(path)
    storageNode.ReadData(parcellationQueryNode)
    slicer.mrmlScene.RemoveNode(storageNode)

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
      logging.debug("Initializing cell pedigree IDs")
      cellPedigreeIds = vtk.vtkIntArray()
      cellPedigreeIds.SetName("cellPedigree")
      cellPedigreeIds.SetNumberOfValues(polyData.GetNumberOfCells())
      for i in range(polyData.GetNumberOfCells()):
        cellPedigreeIds.SetValue(i, i)
      origModelNode.AddCellScalars(cellPedigreeIds)

    pointData = polyData.GetPointData()
    pointPedigreeArray = pointData.GetArray("pointPedigree")
    if pointPedigreeArray is None or pointPedigreeArray.GetClassName() != "vtkDoubleArray":
      logging.debug("Initializing point pedigree IDs")
      pointPedigreeIds = vtk.vtkDoubleArray()
      pointPedigreeIds.SetName("pointPedigree")
      pointPedigreeIds.SetNumberOfValues(polyData.GetNumberOfPoints())
      for i in range(polyData.GetNumberOfPoints()):
        pointPedigreeIds.SetValue(i, i)
      origModelNode.AddPointScalars(pointPedigreeIds)

  def exportOutputToSurfaceLabel(self, parameterNode, surfacesToExport=[]):
    logging.debug("Starting export to surface label")

    origSurfaceNode = parameterNode.GetNodeReference(self.ORIG_MODEL_REFERENCE)
    pialSurfaceNode = parameterNode.GetNodeReference(self.PIAL_MODEL_REFERENCE)
    inflatedSurfaceNode = parameterNode.GetNodeReference(self.INFLATED_MODEL_REFERENCE)
    if origSurfaceNode is None or (origSurfaceNode is None and pialSurfaceNode is None and inflatedSurfaceNode is None):
      logging.error("exportOutputToSurfaceLabel: Invalid surface node")
      return

    self.initializePedigreeIds(parameterNode)

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
      if outputSurfaceNode and len(surfacesToExport) != 0 and not outputSurfaceNode.GetName() in surfacesToExport:
        continue

      polyData = outputSurfaceNode.GetPolyData()
      if polyData is None:
        logging.debug(str(outputSurfaceNode.GetName()) + " polydata is empty")
        continue

      cellData = polyData.GetCellData()
      cellPedigreeArray = cellData.GetArray("cellPedigree")
      if cellPedigreeArray is None:
        logging.debug(str(outputSurfaceNode.GetName()) + " cell pedigree is missing")
        continue

      for cellIndex in range(cellPedigreeArray.GetNumberOfValues()):
        cellId = cellPedigreeArray.GetValue(cellIndex)
        labelArray.SetValue(cellId, modelIndex+1)

    origSurfaceNode.GetPolyData().GetCellData().AddArray(labelArray)
    if pialSurfaceNode:
      pialSurfaceNode.GetPolyData().GetCellData().AddArray(labelArray)
    if inflatedSurfaceNode:
      inflatedSurfaceNode.GetPolyData().GetCellData().AddArray(labelArray)

    # Update color table
    self.updateParcellationColorNode()
    logging.debug("Finish export to surface label")

    # Update outline polydata
    self.updateLabelOutlinePolyData()

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
    lookupTable.SetTableRange(0.0, numberOfOutputModels)
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
    if seedNode is None:
      return

    manuallyPlacedAttribute = seedNode.GetAttribute(self.MANUALLY_PLACED_ATTRIBUTE_NAME)
    if manuallyPlacedAttribute == "TRUE":
      return

    if manuallyPlacedAttribute is None and seedNode.GetNumberOfControlPoints() != 0:
      # Scene was created before auto seed placement was added.
      # Only update the seeds if the seed node doesn't have any control points.
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
    if numberOfRelativeNodes == 0:
      return

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

  def copyMarkupPoints(self, sourceNode, destinationNode):
    """
    Copy the position of the control points in the source node to the destination node.
    Copied point positions are defined in World coordinates.
    """
    if sourceNode is None:
      logging.error("Source node does not exist")
      return
    if destinationNode is None:
      logging.error("Destination node does not exist")
      return
    if sourceNode == destinationNode:
      logging.warning("Source and destination node are the same")
      return

    logging.debug("Copying " +
      sourceNode.GetName() + " (" + sourceNode.GetID() + ") to " +
      destinationNode.GetName() + " (" + destinationNode.GetID() + ")")

    controlPoints_World = vtk.vtkPoints()
    sourceNode.GetControlPointPositionsWorld(controlPoints_World)
    destinationNode.SetControlPointPositionsWorld(controlPoints_World)

  def getPlaneIntersectionVisible(self):
    if self.parameterNode is None:
      return False
    return self.parameterNode.GetParameter(self.PLANE_INTERSECTION_VISIBILITY_NAME) == str(True)

  def setPlaneIntersectionVisible(self, visible):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.PLANE_INTERSECTION_VISIBILITY_NAME, str(visible))
    if visible:
      self.updateAllPlaneIntersections(self.getParameterNode())

  def setIntersectionGlyphType(self, glyphType):
    if self.parameterNode is None:
      return
    glyphTypeString = slicer.vtkMRMLMarkupsDisplayNode.GetGlyphTypeAsString(glyphType)
    self.parameterNode.SetParameter(self.CURVE_INTERSECTION_GLYPH_TYPE_NAME, glyphTypeString)

  def getIntersectionGlyphType(self):
    if self.parameterNode is None:
      return slicer.vtkMRMLMarkupsDisplayNode.Cross2D
    glyphType = self.parameterNode.GetParameter(self.CURVE_INTERSECTION_GLYPH_TYPE_NAME)
    if glyphType == "":
      return slicer.vtkMRMLMarkupsDisplayNode.Cross2D
    return slicer.vtkMRMLMarkupsDisplayNode.GetGlyphTypeFromString(glyphType)

  def setIntersectionGlyphScale(self, glyphScale):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.CURVE_INTERSECTION_GLYPH_SCALE_NAME, str(glyphScale))

  def getIntersectionGlyphScale(self):
    if self.parameterNode is None:
      return 0.5
    glyphScaleString = self.parameterNode.GetParameter(self.CURVE_INTERSECTION_GLYPH_SCALE_NAME)
    if glyphScaleString == "":
      return 0.5
    return float(glyphScaleString)

  def setRedLineVisibility(self, visibility):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.CURVE_VISIBILITY_RED_VIEW, "TRUE" if visibility else "FALSE")

  def getRedLineVisibility(self):
    if self.parameterNode is None:
      return
    return True if self.parameterNode.GetParameter(self.CURVE_VISIBILITY_RED_VIEW) == "TRUE" else False

  def setGreenLineVisibility(self, visibility):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.CURVE_VISIBILITY_GREEN_VIEW, "TRUE" if visibility else "FALSE")

  def getGreenLineVisibility(self):
    if self.parameterNode is None:
      return
    return True if self.parameterNode.GetParameter(self.CURVE_VISIBILITY_GREEN_VIEW) == "TRUE" else False

  def setYellowLineVisibility(self, visibility):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.CURVE_VISIBILITY_YELLOW_VIEW, "TRUE" if visibility else "FALSE")

  def getYellowLineVisibility(self):
    if self.parameterNode is None:
      return
    return True if self.parameterNode.GetParameter(self.CURVE_VISIBILITY_YELLOW_VIEW) == "TRUE" else False

  def setRedIntersectionVisibility(self, visibility):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_RED_VIEW, "TRUE" if visibility else "FALSE")

  def getRedIntersectionVisibility(self):
    if self.parameterNode is None:
      return
    return True if self.parameterNode.GetParameter(self.INTERSECTION_VISIBILITY_RED_VIEW) == "TRUE" else False

  def setGreenIntersectionVisibility(self, visibility):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_GREEN_VIEW, "TRUE" if visibility else "FALSE")

  def getGreenIntersectionVisibility(self):
    if self.parameterNode is None:
      return
    return True if self.parameterNode.GetParameter(self.INTERSECTION_VISIBILITY_GREEN_VIEW) == "TRUE" else False

  def setYellowIntersectionVisibility(self, visibility):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.INTERSECTION_VISIBILITY_YELLOW_VIEW, "TRUE" if visibility else "FALSE")

  def getYellowIntersectionVisibility(self):
    if self.parameterNode is None:
      return
    return True if self.parameterNode.GetParameter(self.INTERSECTION_VISIBILITY_YELLOW_VIEW) == "TRUE" else False

  def getLabelVisibility(self):
    return self.getParameterNode().GetParameter(self.LABEL_TEXT_VISIBILITY) == str(True)

  def setLabelVisibility(self, visibility):
     self.getParameterNode().SetParameter(self.LABEL_TEXT_VISIBILITY, str(visibility))

  def getLabelOutlineVisible(self):
    if self.parameterNode is None:
      return False
    return self.parameterNode.GetParameter(self.LABEL_OUTLINE_VISIBILITY_NAME) == str(True)

  def setLabelOutlineVisible(self, visible):
    if self.parameterNode is None:
      return
    self.parameterNode.SetParameter(self.LABEL_OUTLINE_VISIBILITY_NAME, str(visible))
    self.updateLabelOutlineVisibility()

  def updateLabelOutlineVisibility(self):
    visible = self.getLabelOutlineVisible()
    if visible:
      self.updateLabelOutlinePolyData()

    baseViewIds = ["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow"]
    outlineNodes = self.getLabelOutlineNodes(self.parameterNode) #TODO: Update parameter node
    for outlineNode in outlineNodes:
      outlineNode.SetDisplayVisibility(visible)
      displayNode = outlineNode.GetDisplayNode()
      displayNode.SetActiveScalar("labels", vtk.vtkDataObject.POINT)
      displayNode.SetAndObserveColorNodeID(self.getParcellationColorNode().GetID())
      displayNode.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
      displayNode.SetScalarVisibility(True)
      displayNode.SetInterpolation(slicer.vtkMRMLDisplayNode.FlatInterpolation)
      displayNode.SetLineWidth(4.0)

      viewIds = baseViewIds[:]
      nodeType = outlineNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME)
      if nodeType == self.ORIG_NODE_ATTRIBUTE_VALUE:
        viewIds.append("vtkMRMLViewNodeO")
      elif nodeType == self.PIAL_NODE_ATTRIBUTE_VALUE:
        viewIds.append("vtkMRMLViewNodeP")
      elif nodeType == self.INFLATED_NODE_ATTRIBUTE_VALUE:
        viewIds.append("vtkMRMLViewNodeI")
      displayNode.SetViewNodeIDs(viewIds)

  def updateLabelOverlay(self):
    labelValue = 0
    outputModelNodes = self.getOutputModelNodes()
    for outputModelNode in outputModelNodes:
      labelValue += 1
      outputPolyData = outputModelNode.GetPolyData()
      if outputPolyData is None:
        continue

      pointData = outputPolyData.GetPointData()
      if pointData is None:
        continue

      labelArray = pointData.GetArray("labels")
      if labelArray is None:
        labelArray = vtk.vtkIntArray()
        labelArray.SetName("labels")
        labelArray.SetNumberOfValues(outputPolyData.GetNumberOfPoints())
        labelArray.Fill(labelValue)
        pointData.AddArray(labelArray)

  def updateLabelOutlinePolyData(self):
    parameterNode = self.parameterNode #TODO: Update parameter node

    self.initializePedigreeIds(parameterNode)
    self.updateLabelOverlay()
    outputModelNodes = self.getOutputModelNodes()
    appendFilter = vtk.vtkAppendPolyData()
    for outputModelNode in outputModelNodes:
      outputPolyData = outputModelNode.GetPolyData()
      if not outputPolyData or outputPolyData.GetNumberOfPoints() == 0:
        continue

      boundaryEdges = vtk.vtkFeatureEdges()
      boundaryEdges.SetInputData(outputPolyData)
      boundaryEdges.BoundaryEdgesOn()
      boundaryEdges.FeatureEdgesOff()
      boundaryEdges.NonManifoldEdgesOff()
      boundaryEdges.ManifoldEdgesOff()

      boundaryStrips = vtk.vtkStripper()
      boundaryStrips.SetInputConnection(boundaryEdges.GetOutputPort())

      appendFilter.AddInputConnection(boundaryStrips.GetOutputPort())
    appendFilter.Update()

    outlinePolyData = appendFilter.GetOutput()

    origOutlinePolyData = vtk.vtkPolyData()
    origOutlinePolyData.DeepCopy(outlinePolyData)
    self.convertToFreeSurferPointIds(parameterNode, origOutlinePolyData)

    labelArray = outlinePolyData.GetPointData().GetArray("labels")
    pointPedigreeArray = outlinePolyData.GetPointData().GetArray("pointPedigree")
    if pointPedigreeArray is None:
      logging.error("Invalid point pedigree array")
      return

    newLabelArray = vtk.vtkIntArray()
    newLabelArray.SetName("labels")
    newLabelArray.SetNumberOfValues(origOutlinePolyData.GetNumberOfPoints())
    newLabelArray.Fill(0)
    for i in range(pointPedigreeArray.GetNumberOfValues()):
      pointID = round(pointPedigreeArray.GetValue(i))
      labelValue = labelArray.GetValue(i)
      newLabelArray.SetValue(pointID, labelValue)

    origOutlineNode = None
    pialOutlineNode = None
    inflatedOutlineNode = None

    self.createLabelOutlineNodes(parameterNode)
    outlineNodes = self.getLabelOutlineNodes(parameterNode)
    for outlineNode in outlineNodes:
      outlineNode.SetDisplayVisibility(self.getLabelOutlineVisible())
      nodeType = outlineNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME)
      if nodeType == self.ORIG_NODE_ATTRIBUTE_VALUE:
        origOutlineNode = outlineNode
      elif nodeType == self.PIAL_NODE_ATTRIBUTE_VALUE:
        pialOutlineNode = outlineNode
      elif nodeType == self.INFLATED_NODE_ATTRIBUTE_VALUE:
        inflatedOutlineNode = outlineNode

    origModelNode = self.getOrigModelNode(parameterNode)
    pialModelNode = self.getPialModelNode(parameterNode)
    inflatedModelNode = self.getInflatedModelNode(parameterNode)
    modelAndOutlines = [(origModelNode, origOutlineNode), (pialModelNode, pialOutlineNode), (inflatedModelNode, inflatedOutlineNode)]
    for surfaceModelNode, outlineModelNode in modelAndOutlines:
      if not surfaceModelNode or not outlineModelNode:
        continue
      outlinePolyData = vtk.vtkPolyData()
      outlinePolyData.DeepCopy(origOutlinePolyData)
      points = vtk.vtkPoints()
      points.DeepCopy(surfaceModelNode.GetPolyData().GetPoints())
      outlinePolyData.SetPoints(points)
      outlinePolyData.GetPointData().AddArray(newLabelArray)
      outlineModelNode.SetAndObservePolyData(outlinePolyData)
      if surfaceModelNode.GetParentTransformNode():
        outlineModelNode.SetAndObserveTransformNodeID(surfaceModelNode.GetParentTransformNode().GetID())
      else:
        outlineModelNode.SetAndObserveTransformNodeID(None)

  def getIntersectionModelNodes(self, planeNode):
    if planeNode is None:
      return []

    numberOfIntersectionNodes = planeNode.GetNumberOfNodeReferences(self.INTERSECTION_MODEL_REFERENCE)
    if numberOfIntersectionNodes == 0:
      return self.createIntersectionModelNodes(planeNode)

    intersectionNodes = []
    for i in range(numberOfIntersectionNodes):
      intersectionNode = planeNode.GetNthNodeReference(self.INTERSECTION_MODEL_REFERENCE, i)
      intersectionNodes.append(intersectionNode)
    return intersectionNodes

  def getInputModelNodes(self, parameterNode):
    if self.parameterNode is None:
      return []

    nodeReferences = [
      self.ORIG_MODEL_REFERENCE,
      self.PIAL_MODEL_REFERENCE,
      self.INFLATED_MODEL_REFERENCE,
      ]
    inputModelNodes = []
    for nodeReference in nodeReferences:
      inputModelNode = parameterNode.GetNodeReference(nodeReference)
      if inputModelNode is None:
        continue
      inputModelNodes.append(inputModelNode)
    return inputModelNodes

  def createLabelOutlineNodes(self, parameterNode):
    if not parameterNode:
      return

    outlineNodes = self.getLabelOutlineNodes(parameterNode)

    for nodeType in self.NODE_TYPES:
      currentOutlineNode = None
      for outlineNode in outlineNodes:
        if outlineNode and outlineNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME) == nodeType:
          currentOutlineNode = outlineNode
          break

      if not currentOutlineNode is None:
        continue

      currentOutlineNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", "LabelOutline_{0}".format(nodeType))
      currentOutlineNode.CreateDefaultDisplayNodes()
      currentOutlineNode.SetDisplayVisibility(False)
      currentOutlineNode.SetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME, nodeType)
      parameterNode.AddNodeReferenceID(self.LABEL_OUTLINE_MODEL_REFERENCE, currentOutlineNode.GetID())

  def getLabelOutlineNodes(self, parameterNode):
    if parameterNode is None:
      return []

    outlineModelNodes = []
    numberOfOutlineNodes = parameterNode.GetNumberOfNodeReferences(self.LABEL_OUTLINE_MODEL_REFERENCE)
    for i in range(numberOfOutlineNodes):
      outlineNode = parameterNode.GetNthNodeReference(self.LABEL_OUTLINE_MODEL_REFERENCE, i)
      if outlineNode is None:
        continue
      outlineModelNodes.append(outlineNode)
    return outlineModelNodes

  def updatePlaneIntersectionVisibility(self):
    visible = self.getPlaneIntersectionVisible()
    inputMarkupNodes = self.getInputMarkupNodes()
    baseViewIds = ["vtkMRMLViewNode1", "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeGreen", "vtkMRMLSliceNodeYellow"]
    for inputMarkupNode in inputMarkupNodes:
      if not inputMarkupNode.IsA("vtkMRMLMarkupsPlaneNode"):
        continue
      intersectionModelNodes = self.getIntersectionModelNodes(inputMarkupNode)
      for intersectionNode in intersectionModelNodes:
        intersectionNode.SetDisplayVisibility(visible)
        viewIds = baseViewIds[:]
        nodeType = intersectionNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME)
        if nodeType == self.ORIG_NODE_ATTRIBUTE_VALUE:
          viewIds.append("vtkMRMLViewNodeO")
        elif nodeType == self.PIAL_NODE_ATTRIBUTE_VALUE:
          viewIds.append("vtkMRMLViewNodeP")
        elif nodeType == self.INFLATED_NODE_ATTRIBUTE_VALUE:
          viewIds.append("vtkMRMLViewNodeI")
        intersectionNode.GetDisplayNode().SetViewNodeIDs(viewIds)

  def getIntersectionModelNodes(self, planeNode):
    if planeNode is None:
      return []

    numberOfIntersectionNodes = planeNode.GetNumberOfNodeReferences(self.INTERSECTION_MODEL_REFERENCE)
    if numberOfIntersectionNodes == 0:
      return self.createIntersectionModelNodes(planeNode)

    intersectionNodes = []
    for i in range(numberOfIntersectionNodes):
      intersectionNode = planeNode.GetNthNodeReference(self.INTERSECTION_MODEL_REFERENCE, i)
      intersectionNodes.append(intersectionNode)
    return intersectionNodes

  def createIntersectionModelNodes(self, planeNode):
    if planeNode is None:
      return []

    intersectionNodes = []
    for nodeType in [self.ORIG_NODE_ATTRIBUTE_VALUE, self.PIAL_NODE_ATTRIBUTE_VALUE, self.INFLATED_NODE_ATTRIBUTE_VALUE]:
      nodeName = planeNode.GetName() + "_" + nodeType + "_Intersection"
      intersectionNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", nodeName)
      intersectionNode.SetAndObservePolyData(vtk.vtkPolyData())
      intersectionNode.SetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME, nodeType)
      intersectionNode.CreateDefaultDisplayNodes()
      planeNode.AddNodeReferenceID(self.INTERSECTION_MODEL_REFERENCE, intersectionNode.GetID())
      intersectionNodes.append(intersectionNode)
    self.updatePlaneIntersection(self.parameterNode, planeNode)
    self.updatePlaneIntersectionDisplay(planeNode)
    return intersectionNodes

  def onPlaneNodeModified(self, planeNode, eventId=None, callData=None):
    self.updatePlaneIntersection(self.parameterNode, planeNode)

  def onPlaneDisplayModified(self, planeNode, eventId=None, callData=None):
    self.updatePlaneIntersectionDisplay(planeNode)

  def updatePlaneIntersectionDisplay(self, planeNode):
    planeDisplayNode = planeNode.GetDisplayNode()
    intersectionModelNodes = self.getIntersectionModelNodes(planeNode)
    visible = self.getPlaneIntersectionVisible()
    for intersectionModelNode in intersectionModelNodes:
      intersectionModelNode.GetDisplayNode().SetColor(planeDisplayNode.GetSelectedColor())
      intersectionModelNode.SetDisplayVisibility(visible)

  def updateAllPlaneIntersections(self, parameterNode):
    inputMarkupNodes = self.getInputMarkupNodes()
    for inputMarkupNode in inputMarkupNodes:
      if inputMarkupNode is None or not inputMarkupNode.IsA("vtkMRMLMarkupsPlaneNode"):
        continue
      self.updatePlaneIntersection(parameterNode, inputMarkupNode)

  def updatePlaneIntersection(self, parameterNode, planeNode):
    # Only interested in plane nodes
    if not planeNode or not planeNode.IsA("vtkMRMLMarkupsPlaneNode"):
      logging.error("updatePlaneIntersection: Invalid plane node")
      return

    origModelNode = self.getOrigModelNode(parameterNode)
    if origModelNode is None or origModelNode.GetPolyData() is None:
      return

    origIntersectionPolyData = vtk.vtkPolyData()
    if planeNode.GetIsPlaneValid():

      self.initializePedigreeIds(parameterNode)

      transformFilter = vtk.vtkTransformPolyDataFilter()
      transformFilter.SetInputData(origModelNode.GetPolyData())
      modelToWorldTransform = vtk.vtkGeneralTransform()
      slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(origModelNode.GetParentTransformNode(), None, modelToWorldTransform);
      transformFilter.SetTransform(modelToWorldTransform)

      planeExtractor = vtk.vtkExtractPolyDataGeometry()
      planeExtractor.SetInputConnection(transformFilter.GetOutputPort())
      planeExtractor.ExtractInsideOff()
      planeExtractor.ExtractBoundaryCellsOff()

      boundaryEdges = vtk.vtkFeatureEdges()
      boundaryEdges.SetInputConnection(planeExtractor.GetOutputPort())
      boundaryEdges.BoundaryEdgesOn()
      boundaryEdges.FeatureEdgesOff()
      boundaryEdges.NonManifoldEdgesOff()
      boundaryEdges.ManifoldEdgesOff()

      boundaryStrips = vtk.vtkStripper()
      boundaryStrips.SetInputConnection(boundaryEdges.GetOutputPort())

      origin_World = [0.0, 0.0, 0.0]
      planeNode.GetOriginWorld(origin_World)
      normal_World = [0.0, 0.0, 0.0]
      planeNode.GetNormalWorld(normal_World)

      plane = vtk.vtkPlane()
      plane.SetOrigin(origin_World)
      plane.SetNormal(normal_World)
      planeExtractor.SetImplicitFunction(plane)
      boundaryStrips.Update()
      origIntersectionPolyData = vtk.vtkPolyData()
      origIntersectionPolyData.DeepCopy(boundaryStrips.GetOutput())
      self.convertToFreeSurferPointIds(parameterNode, origIntersectionPolyData)

    origIntersectionNode = None
    pialIntersectionNode = None
    inflatedIntersectionNode = None
    intersectionModelNodes = self.getIntersectionModelNodes(planeNode)
    for intersectionNode in intersectionModelNodes:
      intersectionNode.SetDisplayVisibility(self.getPlaneIntersectionVisible())
      nodeType = intersectionNode.GetAttribute(self.NODE_TYPE_ATTRIBUTE_NAME)
      if nodeType == self.ORIG_NODE_ATTRIBUTE_VALUE:
        origIntersectionNode = intersectionNode
      elif nodeType == self.PIAL_NODE_ATTRIBUTE_VALUE:
        pialIntersectionNode = intersectionNode
      elif nodeType == self.INFLATED_NODE_ATTRIBUTE_VALUE:
        inflatedIntersectionNode = intersectionNode

    pialModelNode = self.getPialModelNode(parameterNode)
    inflatedModelNode = self.getInflatedModelNode(parameterNode)
    modelAndIntersections = [(origModelNode, origIntersectionNode), (pialModelNode, pialIntersectionNode), (inflatedModelNode, inflatedIntersectionNode)]
    for surfaceModelNode, intersectionModelNode in modelAndIntersections:
      if not surfaceModelNode or not intersectionModelNode:
        continue
      intersectionPolyData = vtk.vtkPolyData()
      intersectionPolyData.DeepCopy(origIntersectionPolyData)
      points = vtk.vtkPoints()
      points.DeepCopy(surfaceModelNode.GetPolyData().GetPoints())
      intersectionPolyData.SetPoints(points)
      intersectionModelNode.SetAndObservePolyData(intersectionPolyData)
      if surfaceModelNode.GetParentTransformNode():
        intersectionModelNode.SetAndObserveTransformNodeID(surfaceModelNode.GetParentTransformNode().GetID())
      else:
        intersectionModelNode.SetAndObserveTransformNodeID(None)

  def convertToFreeSurferPointIds(self, parameterNode, polyData):
    if parameterNode is None:
      logging.error("Invalid parameter node")

    pointData = polyData.GetPointData()
    pedigreeArray = pointData.GetArray("pointPedigree")
    if pedigreeArray is None:
      logging.error("Could not find pointPedigree array")
      return

    origModelNode = self.getOrigModelNode(parameterNode)
    if origModelNode is None or origModelNode.GetPolyData() is None:
      logging.error("Could not find orig polydata")
      return

    # Iterate through all of the lines and find the corresponding pedigree point ids for the original surface.
    # Restore the original point ids to the line cells.
    newLines = vtk.vtkCellArray()
    oldLines = polyData.GetLines()
    oldLine = vtk.vtkIdList()
    polyData.GetLines().InitTraversal()
    while(polyData.GetLines().GetNextCell(oldLine)):
      newLine = vtk.vtkIdList()
      for pointIndex in range(oldLine.GetNumberOfIds()):
        oldPointId = oldLine.GetId(pointIndex)
        newPointId = round(pedigreeArray.GetValue(oldPointId))
        newLine.InsertNextId(newPointId)
      newLines.InsertNextCell(newLine)
    polyData.Initialize()
    polyData.SetPoints(origModelNode.GetPolyData().GetPoints())
    polyData.SetLines(newLines)

  def convertPointDataOverlayToModelNode(self, overlayModelNode, importOverlay, destinationNode, insideLabelValue=3):
    logging.debug("Convert point data to model node")
    if overlayModelNode and overlayModelNode.GetPolyData() and overlayModelNode.GetPolyData().GetPointData():
      importArray = overlayModelNode.GetPolyData().GetPointData().GetArray(importOverlay)
    if importArray is None:
      logging.error("convertOverlayToModelNode: Could not find array " + str(importOverlay))
      return

    overlayModel = overlayModelNode.GetPolyData()
    cellIds = vtk.vtkIdList()
    for cellId in range(overlayModel.GetNumberOfPolys()):
      pointIds = vtk.vtkIdList()
      overlayModel.GetCellPoints(cellId, pointIds)
      includedCell = True
      for pointIndex in range(pointIds.GetNumberOfIds()):
        pointId = pointIds.GetId(pointIndex)
        labelValue = importArray.GetValue(pointId)
        if labelValue != insideLabelValue:
          includedCell = False
          break

      if includedCell:
        cellIds.InsertNextId(cellId)

    extractCells = vtk.vtkExtractCells()
    extractCells.SetInputData(overlayModel)
    extractCells.SetCellList(cellIds)
    geometryFilter = vtk.vtkGeometryFilter()
    geometryFilter.SetInputConnection(extractCells.GetOutputPort())
    geometryFilter.Update()
    destinationPolyData = geometryFilter.GetOutput()

    cleanFilter = vtk.vtkCleanPolyData()
    cleanFilter.SetInputData(destinationPolyData)
    cleanFilter.Update()
    destinationNode.SetAndObservePolyData(cleanFilter.GetOutput())

  def convertCellDataOverlayToModelNode(self, overlayModelNode, importOverlay, destinationNode, insideLabelValue=3):
    logging.debug("Convert cell data to model node")
    if overlayModelNode and overlayModelNode.GetPolyData() and overlayModelNode.GetPolyData().GetPointData():
      importArray = overlayModelNode.GetPolyData().GetCellData().GetArray(importOverlay)
    if importArray is None:
      logging.error("convertOverlayToModelNode: Could not find array " + str(importOverlay))
      return

    overlayModel = overlayModelNode.GetPolyData()
    cellIds = vtk.vtkIdList()
    for cellId in range(overlayModel.GetNumberOfPolys()):
      if importArray.GetValue(cellId) == insideLabelValue:
        cellIds.InsertNextId(cellId)

    extractCells = vtk.vtkExtractCells()
    extractCells.SetInputData(overlayModel)
    extractCells.SetCellList(cellIds)
    geometryFilter = vtk.vtkGeometryFilter()
    geometryFilter.SetInputConnection(extractCells.GetOutputPort())
    geometryFilter.Update()
    destinationPolyData = geometryFilter.GetOutput()

    cleanFilter = vtk.vtkCleanPolyData()
    cleanFilter.SetInputData(destinationPolyData)
    cleanFilter.Update()
    destinationNode.SetAndObservePolyData(cleanFilter.GetOutput())

  def convertOverlayToModelNode(self, overlayModelNode, importOverlay, destinationNode, insideLabelValue=3):
    """
    Convert a scalar overlay from a model node to a new model node
    Uses the "label" overlay from FreeSurfer (default, 3 inside, 1000 outside)
    Replaces the contents of the destination node polydata
    """

    if overlayModelNode and overlayModelNode.GetPolyData() and overlayModelNode.GetPolyData().GetCellData():
      if overlayModelNode.GetPolyData().GetCellData().GetArray(importOverlay):
        self.convertCellDataOverlayToModelNode(overlayModelNode, importOverlay, destinationNode, insideLabelValue)
        return

    if overlayModelNode and overlayModelNode.GetPolyData() and overlayModelNode.GetPolyData().GetPointData():
      if overlayModelNode.GetPolyData().GetPointData().GetArray(importOverlay):
        self.convertPointDataOverlayToModelNode(overlayModelNode, importOverlay, destinationNode, insideLabelValue)
        return
