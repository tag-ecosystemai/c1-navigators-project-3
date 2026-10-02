from app.schemas.ai_results import AnomalyDetectionResult
class AnomalyDetectionInterface:
 async def detect(self,transactions): return AnomalyDetectionResult(findings=['Mock anomaly detection completed.'])
anomaly_detection=AnomalyDetectionInterface()
