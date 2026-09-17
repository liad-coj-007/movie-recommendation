python src/model/training/export.py
echo "finished exporting"
python src/model/training/train.py 
echo "finish training"
rm -rf data_chunks
