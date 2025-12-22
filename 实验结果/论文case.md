增加work识别和code生成部分重试或者改进办法

### case 1.1

正确

#### 描述

我想要把deep sequoia和pubmed分别用bigtranslate翻译之后，将翻译后的deep sequoia和pubmed与bigtranslate打包出售，请问违反了什么许可证问题

#### 生成的代码

```python
from main_case import *
deep_sequoia_text = Work('Deep-sequoia', 'data', 'raw', 'LGPL-LR') # Corpus
pubmed_text = Work('PubMed', 'data', 'raw', 'CC-BY-NC-ND-4.0') # Corpus
bigtranslate_model = Work('BigTranslate', 'model', 'raw', 'GPL-3.0') # Text Translation
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)

translated = [embed(ds, bigtranslate_model) for ds in [deep_sequoia_text, pubmed_text]]
new_work = combine(translated + [bigtranslate_model])

new_work.form = 'raw'
par.analysis(new_work, open_policy='sell')
new_work.summary()
```

### case 1.2

正确

#### 描述

我想把arxiv和stack exchange分别用bigtranslate翻译之后，与deep sequoia和free law打包出售，请问违反了什么许可证问题

#### 生成的代码

```python
from main_case import *
arxiv_text = Work('arXiv', 'data', 'raw', 'CC-BY-NC-SA-4.0') # Corpus
stack_exchange_text = Work('StackExchange', 'data', 'raw', 'CC-BY-SA-4.0') # Corpus
bigtranslate_model = Work('BigTranslate', 'model', 'raw', 'GPL-3.0') # Text Translation
deep_sequoia_text = Work('Deep-sequoia', 'data', 'raw', 'LGPL-LR') # Corpus
free_law_text = Work('FreeLaw', 'data', 'raw', 'CC-BY-ND-4.0') # Corpus
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)

translated = [embed(arxiv_text, bigtranslate_model), embed(stack_exchange_text, bigtranslate_model)]
new_work = combine(translated + [deep_sequoia_text, free_law_text])

new_work.form = 'raw'
par.analysis(new_work, open_policy='sell')
new_work.summary()
```

### case 2.1

正确

#### 描述

我用wiki微调了bert，将其与baize和bloom组成MoE后，让整个模型为外界提供API服务，请问违反了什么许可证问题

#### 生成的代码

```python
from main_case import *
wiki_text = Work('Wikipedia', 'data', 'raw', 'CC-BY-SA-4.0') # Corpus
bert_model = Work('BERT', 'model', 'raw', 'Apache-2.0') # Text
baize_model = Work('Baize', 'model', 'raw', 'GPL-3.0') # Chatbot
bloom_model = Work('BLOOM', 'model', 'raw', 'BigScience-BLOOM-RAIL-1.0') # Text Generation
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)
finetuned_bert = finetune(bert_model, wiki_text)
new_work = combine([finetuned_bert, baize_model, bloom_model])
new_work.form = 'saas'
par.analysis(new_work, open_policy='sell')
new_work.summary()
```

### case 2.2

正确

#### 描述

我用Flickr微调了MaskFormer，将其与i2vgen和detr组成MoE后，将整个模型共享，请问违反了什么许可证问题


#### 生成的代码

```python
from main_case import *
flickr_img = Work('Flickr', 'data', 'raw', 'CC-BY-NC-SA-4.0') # Image
maskformer_model = Work('MaskFormer', 'model', 'raw', 'CC-BY-NC-4.0') # Image Segmentation
i2vgen_model = Work('I2VGen-XL', 'model', 'raw', 'CC-BY-NC-ND-4.0') # Image2Video
detr_model = Work('DETR', 'model', 'raw', 'Apache-2.0') # Image Segmentation
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)

finetuned_maskformer = finetune(maskformer_model, flickr_img)
new_work = combine([finetuned_maskformer, i2vgen_model, detr_model])

new_work.form = 'raw'
par.analysis(new_work, open_policy='share')
new_work.summary()
```

### case 3

generate函数使用方法有误，修改后成功

#### 描述

我将jamendo输入由whisper、baize、stable diffusion、i2vgen-xl几个模型依次组成的生成链，将输出的数据集共享出去，请问违反了什么许可证问题


#### 生成的代码

```python
from main_case import *
jamendo_music = Work('Jamendo', 'data', 'raw', 'CC-BY-NC-ND-4.0') # Music
whisper_model = Work('Whisper', 'model', 'raw', 'MIT') # Voice2Text
baize_model = Work('Baize', 'model', 'raw', 'GPL-3.0') # Chatbot
stable_diffusion_mode = Work('StableDiffusion', 'model', 'raw', 'CreativeML-OpenRAIL-M') # Text2Image
i2vgen_model = Work('I2VGen-XL', 'model', 'raw', 'CC-BY-NC-ND-4.0') # Image2Video
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)

jamendo_output = generate([whisper_model, baize_model, stable_diffusion_mode, i2vgen_model])
new_work = combine([jamendo_output])

new_work.form = 'raw'
par.analysis(new_work, open_policy='share')
new_work.summary()
```

修正版

描述

我将jamendo输入由whisper、baize、stable diffusion、i2vgen-xl几个模型依次组成的生成链递归调用，前一个模型的输出作为后一个模型的输入，例如，将jamendo输入whisper，输出得到的jamendo_1，将jamendo_1输入baize，以此类推。将最后输出的数据集共享出去，请问违反了什么许可证问题

生成的代码

```python
intermediate_1 = generate(whisper_model, jamendo_music)
intermediate_2 = generate(baize_model, intermediate_1)
final_output = generate(stable_diffusion_mode, intermediate_2)
new_work = generate(i2vgen_model, final_output)
new_work.form = 'raw'
par.analysis(new_work, open_policy='share')
new_work.summary()
```

### case 3.1


#### 描述

我将jamendo输入由whisper、baize、stable diffusion、i2vgen-xl几个模型依次组成的生成链，前一个模型的输出作为后一个模型的输入，将过程中用到的模型和输出的数据集组合起来，最后一起共享出去，请问违反了什么许可证问题


#### 生成的代码

```python

```

### case 4.1

正确

#### 描述

利用wikimedia数据集将i2vgen的知识蒸馏到xclip中，然后将此模型与maskformer和whisper进行融合后出售。

#### 生成的代码

```python
from main_case import *
wikimedia_img = Work('Wikimedia', 'data', 'raw', 'CC-BY-SA-4.0') # Image
i2vgen_model = Work('I2VGen-XL', 'model', 'raw', 'CC-BY-NC-ND-4.0') # Image2Video
xclip_model = Work('X-Clip', 'model', 'raw', 'MIT') # Video2Text
maskformer_model = Work('MaskFormer', 'model', 'raw', 'CC-BY-NC-4.0') # Image Segmentation
whisper_model = Work('Whisper', 'model', 'raw', 'MIT') # Voice2Text
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)

distilled_x_clip = distill([wikimedia_img, i2vgen_model], xclip_model)
new_work = amalgamate([distilled_x_clip, maskformer_model, whisper_model])

new_work.form = 'raw'
par.analysis(new_work, open_policy='sell')
new_work.summary()
```

### case 4.2
正确

#### 描述

我用wiki微调了bert，将其与baize和bloom组成MoE后，让整个模型为外界提供API服务，请问违反了什么许可证问题

#### 生成的代码

```python
from main_case import *
wiki_text = Work('Wikipedia', 'data', 'raw', 'CC-BY-SA-4.0') # Corpus
bloom_model = Work('BLOOM', 'model', 'raw', 'BigScience-BLOOM-RAIL-1.0') # Text Generation
bert_model = Work('BERT', 'model', 'raw', 'Apache-2.0') # Text
llama2_model = Work('Llama2', 'model', 'raw', 'Llama2') # Text Generation
bigtranslate_model = Work('BigTranslate', 'model', 'raw', 'GPL-3.0') # Text Translation
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)

distilled_bert = distill([bloom_model], bert_model)
new_work = amalgamate([distilled_bert, llama2_model, bigtranslate_model])

new_work.form = 'raw'
par.analysis(new_work, open_policy='sell')
new_work.summary()
```

### case 5

错误1：generate应该是逐层调用，现在是一次调用，中间work缺少调用关系
错误2：dataset_B和vimeo_video应该是amalgamate的关系，识别成了combine

#### 描述

    将stocksnap、midjourney、thingverse三个数据集进行融合，记作数据集A。
    将ccmixter输入由whisper、baize、stable diffusion、i2vgen-xl几个模型依次组成的生成链得到输出，记作数据集B。
    将数据集B与vimeo融合得到数据集C。
    将数据集A与数据集C组合后销售。，请问违反了什么许可证问题？


#### 生成的代码

```python
from main_case import *
stocksnap_img = Work('StockSnap', 'data', 'raw', 'CC0-1.0') # Image
midjourney_img = Work('Midjourney_gen', 'data', 'raw', 'CC-BY-NC-4.0') # Image
thingverse_3d = Work('Thingverse', 'data', 'raw', 'CC-BY-NC-SA-4.0') # 3D Model
ccmixter_music = Work('ccMixter', 'data', 'raw', 'CC-BY-NC-4.0') # Music
whisper_model = Work('Whisper', 'model', 'raw', 'MIT') # Voice2Text
baize_model = Work('Baize', 'model', 'raw', 'GPL-3.0') # Chatbot
stable_diffusion_mode = Work('StableDiffusion', 'model', 'raw', 'CreativeML-OpenRAIL-M') # Text2Image
i2vgen_model = Work('I2VGen-XL', 'model', 'raw', 'CC-BY-NC-ND-4.0') # Image2Video
vimeo_video = Work('Vimeo', 'data', 'raw', 'CC-BY-NC-ND-4.0') # Video
works = [ob for ob in gc.get_objects() if isinstance(ob, Work)]
par.register_license(works)

dataset_A = amalgamate([stocksnap_img, midjourney_img, thingverse_3d])
dataset_B = generate(ccmixter_music, [whisper_model, baize_model, stable_diffusion_mode, i2vgen_model])
dataset_C = combine([dataset_B, vimeo_video])
new_work = combine([dataset_A, dataset_C])

new_work.form = 'raw'
par.analysis(new_work, open_policy='sell')
new_work.summary()
```

修改后的生成代码：

```python
dataset_a = amalgamate([stocksnap_img, midjourney_img, thingverse_3d])
first_generation_output = generate(ccmixter_music, [whisper_model])
second_generation_output = generate(first_generation_output, [baize_model])
third_generation_output = generate(second_generation_output, [stable_diffusion_mode])
final_dataset_b = generate(third_generation_output, [i2vgen_model])
dataset_c = amalgamate([final_dataset_b, vimeo_video])
new_work = combine([dataset_a, dataset_c])
```

成功！
