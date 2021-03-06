# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
#from IPython import get_ipython

# %% [markdown]
# # Generate Gpt-2 Examples #
# 
# **prompt_text**:change the prompt to a text of your choice  
# **response_length**: This is the maximum length of any response. It may choose to create shorter response itself. This cannot be longer than 1024  
# **output_file**: This should be a .csv file. It can be downloaded an analyzed. If this is run multiple times, it will append all answers into the file.  
# **num_of_responses**: This is usually a max of 4 for K80 GPU. It is possible that even at 4, the process may error. If this is the case rerun.  
#   
# **IN CASE OF ERROR**  
# The process may error because the GPU gets filled up. Everytime you run this, make sure that the GPU starts with 0 memory used. The !Nvidia-smi command shows that.   
# In the middle column it should say "0MB/11441MB"    
# if it does not. The GPU needs to be cleared.  
# Clear the GPU by clicking on the top menu "Kernel->Restart Kernel" Then rerun the notebook from the top cell.  

# %%

#prompt_text="If God is defined as something that is all powerful and all knowing, a strong artificial intelligence might be an actual God. If this happens the implications for religion are"
#max reponse_length 1024
#response_length=1000
#output_file will be created if it doesn't exist, otherwise answers will be appended
output_file="results.csv"
#max 4 (k80 gpu)
#num_of_responses=20


# %%
#from ipyexperiments import *


# %%
#get_ipython().system('nvidia-smi')


# %%
all_seq=[]
results=[]
gen_num=0

# %%
import torch
#print(torch.__version__)
#print(torch.cuda.device_count())
import argparse
paraser=argparse.ArgumentParser(description="multi gpu huggingface gpt2 generator")
paraser.add_argument("--prompt",help="prompt to begin response with")
paraser.add_argument("--length",type=int,default=500,help="length of response (default=500)")
paraser.add_argument("--num_of_responses",type=int,default=20,help="number of response to generate, sb divisible by 5, will gen 5 on each gpu")
args=paraser.parse_args()


# %%
def return_results(tokenizer, encoded_prompt, outputs, all_seq):
    generated_sequences=[]
    total_sequence=""
    for generated_sequence_idx, generated_sequence in enumerate(outputs):
            global gen_num
            gen_num+=1
            print("=== GENERATED SEQUENCE {} ===".format(gen_num))
            generated_sequence = generated_sequence.tolist()
            #print(generated_sequence)
            # Decode text
            text = tokenizer.decode(generated_sequence, clean_up_tokenization_spaces=True)
            #print(text)
            # Remove all text after the stop token
            stop_token='<|endoftext|>'
            text = text[: text.find(stop_token) if stop_token else None]

            # Add the prompt at the beginning of the sequence. Remove the excess text that was used for pre-processing
            total_sequence = (
                args.prompt + text[len(tokenizer.decode(encoded_prompt[0], clean_up_tokenization_spaces=True)) :]
            )

            generated_sequences.append(total_sequence)
            print(total_sequence)
            all_seq.append(total_sequence)
    return


# %%
def run_gpt2(gpu, prompt_text,response_length,num_of_responses,all_seq):
    #%%time
    print('starting {} {} {}'.format(gpu,response_length, num_of_responses))
    import numpy as np
    from transformers import GPT2Tokenizer, GPT2LMHeadModel
    import torch
    #n_gpu=torch.cuda.device_count()
    #device = xm.xla_device()
    device=torch.device(gpu)
    tokenizer = GPT2Tokenizer.from_pretrained('/spell/GPT2Model/GPT2Model/')
    model = GPT2LMHeadModel.from_pretrained('/spell/GPT2Model/GPT2Model/')
    #if n_gpu > 1 and not isinstance(model, torch.nn.DataParallel):
    #    model = torch.nn.DataParallel(model)
    model.to(device)
    #model = torch.nn.DataParallel(model, device_ids=[0,1])
    encoded_prompt=tokenizer.encode(prompt_text, add_special_tokens=True,return_tensors="pt")
    encoded_prompt = encoded_prompt.to(device)

    outputs = model.generate(encoded_prompt,response_length,temperature=.8,num_return_sequences=num_of_responses,repetition_penalty=85,do_sample=True,top_k=80,top_p=.85,eos_token_id=50256 )
    if len(outputs.shape) > 2:
        outputs.squeeze_()
    return_results(tokenizer, encoded_prompt, outputs,all_seq)
    del model
    del encoded_prompt
    torch.cuda.empty_cache()
    return 


# %%
from concurrent.futures.thread import ThreadPoolExecutor
import concurrent.futures
gpus=torch.cuda.device_count()
gptresult=[]
print('gpus=',gpus)
#calculate threads for each gpu
threadiv=gpus*5
with ThreadPoolExecutor(max_workers=gpus) as executor:
    totalthreads=int(args.num_of_responses/threadiv)
    print('total runs=',totalthreads)
    for t in range(1,totalthreads+1):
        print('run number ',t)
        for i in range (gpus):
            print('sending to cuda:',str(i))
            #args=("cuda:"+str(i),prompt_text,response_length,num_of_responses,all_seq))
            gptresult.append(executor.submit(run_gpt2,"cuda:"+str(i),args.prompt,args.length,5,all_seq))
        for future in concurrent.futures.as_completed(gptresult):
            print('result=',future.result())
        gptresult=[]

print('all threads complete')


# %%
'''
import time
import nvgpu
keep_going=True
time.sleep(30)
while keep_going:
    time.sleep(5)
    n=nvgpu.gpu_info()
    #print(nvgpu.available_gpus())
    #print ("n=",n, len(n))
    for i in n:
        #print(i)
        print(i["index"],i["mem_used"],end=' ')
        if i["mem_used"]==0:
            keep_going=False
'''


# %%
if len(all_seq)==len(set(all_seq)):
  print('no duplicates')
else:
  print('duplicates found')


# %%
import csv
import os
if os.path.exists(output_file):
    append_flag="a"
else: 
    append_flag="w"
with open (output_file, append_flag) as csvfile:
    writer=csv.writer(csvfile)
    for i in all_seq:
        writer.writerow([args.prompt, i])
    


# %%
print('run complete')


# %%


