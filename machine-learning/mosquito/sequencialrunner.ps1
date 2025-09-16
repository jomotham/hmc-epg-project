echo "Starting sequential run"

python .\model_eval.py --data_path ..\..\tarsalis_data_clean\ --model_path .\unet.py --save_path UNET_Block_Hyper --model_name UNET_Block --optuna > unet_block.txt


python .\model_eval.py --data_path ..\..\tarsalis_data_clean\ --model_path .\unet.py --save_path UNET_Attention_Hyper --model_name UNET_Attention --optuna --attention > unet_attention.txt
