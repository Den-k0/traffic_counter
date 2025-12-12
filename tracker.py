import numpy as np
import math


class CentroidTracker:
    """
    Трекер об'єктів. Присвоює ID та відстежує переміщення центроїдів.
    """
    def __init__(self, maxDisappeared=40):
        self.nextObjectID = 0
        self.objects = {}           # ID -> (x, y)
        self.previous_objects = {}  # ID -> (x, y) (попередня позиція)
        self.labels = {}            # ID -> назва класу
        self.disappeared = {}       # ID -> лічильник відсутності
        self.maxDisappeared = maxDisappeared

    def register(self, centroid, label):
        self.objects[self.nextObjectID] = centroid
        self.previous_objects[self.nextObjectID] = centroid
        self.labels[self.nextObjectID] = label
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        del self.objects[objectID]
        del self.previous_objects[objectID]
        del self.labels[objectID]
        del self.disappeared[objectID]
        return objectID

    def update(self, rects, input_labels):
        deregistered_ids = []

        if len(rects) == 0:
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    deleted = self.deregister(objectID)
                    deregistered_ids.append(deleted)
            return self.objects, self.previous_objects, self.labels, deregistered_ids

        inputCentroids = np.zeros((len(rects), 2), dtype="int")
        for (i, (startX, startY, endX, endY)) in enumerate(rects):
            inputCentroids[i] = (int((startX + endX) / 2.0), int((startY + endY) / 2.0))

        if len(self.objects) == 0:
            for i in range(len(inputCentroids)):
                self.register(inputCentroids[i], input_labels[i])
        else:
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())

            D = []
            for i in range(len(objectCentroids)):
                row = []
                for j in range(len(inputCentroids)):
                    dist = math.hypot(objectCentroids[i][0] - inputCentroids[j][0],
                                      objectCentroids[i][1] - inputCentroids[j][1])
                    row.append(dist)
                D.append(row)
            D = np.array(D)

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            usedRows = set()
            usedCols = set()

            for (row, col) in zip(rows, cols):
                if row in usedRows or col in usedCols: continue
                if D[row, col] > 200: continue

                objectID = objectIDs[row]
                self.previous_objects[objectID] = self.objects[objectID]
                self.objects[objectID] = inputCentroids[col]
                self.labels[objectID] = input_labels[col]
                self.disappeared[objectID] = 0
                usedRows.add(row)
                usedCols.add(col)

            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            for row in unusedRows:
                objectID = objectIDs[row]
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    deleted = self.deregister(objectID)
                    deregistered_ids.append(deleted)

            unusedCols = set(range(0, D.shape[1])).difference(usedCols)
            for col in unusedCols:
                self.register(inputCentroids[col], input_labels[col])

        return self.objects, self.previous_objects, self.labels, deregistered_ids
