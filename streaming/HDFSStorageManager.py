# modules/storage_manager.py
class HDFSStorageManager:
    def __init__(self):
        self.hdfs_base = "hdfs://s1:9000"
        
    def save_raw_data(self, df):
        return df.writeStream \
            .format("parquet") \
            .option("path", f"{self.hdfs_base}/fms/raw-data") \
            .partitionBy("DeviceId", "year", "month", "day") \
            .option("checkpointLocation", "/tmp/checkpoint") \
            .option("compression", "gzip") \
            .trigger(processingTime='30 seconds') \
            .outputMode("append") \
            .start()
    
    def save_processed_data(self, df):
        return df.writeStream \
            .format("delta") \
            .option("path", f"{self.hdfs_base}/fms/processed") \
            .partitionBy("DeviceId") \
            .trigger(processingTime='1 minute') \
            .outputMode("append") \
            .start()
    
    def save_alerts(self, df):
        return df.writeStream \
            .format("json") \
            .option("path", f"{self.hdfs_base}/fms/alerts") \
            .trigger(processingTime='10 seconds') \
            .outputMode("append") \
            .start()