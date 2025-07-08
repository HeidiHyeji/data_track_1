ssh s1 "tmux new-session -d -s spark_preprocess 'spark-submit /home/ec2-user/data_track_1/spark/pipeline/spark_preprocessing_streaming.py'"
