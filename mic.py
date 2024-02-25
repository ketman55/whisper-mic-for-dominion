import io
from pydub import AudioSegment
import speech_recognition as sr
import faster_whisper
import queue
import tempfile
import os
import threading
import click
import torch
import numpy as np

# 設定（fine-tuning）
from transformers import WhisperForConditionalGeneration, WhisperProcessor, WhisperConfig
from datasets import load_dataset, DatasetDict, Dataset, Audio

# 画面に文字を表示させる
import tkinter as tk
import tkinter.font as font

# 音声認識向上のために画像データを参照する
prompt = ""

# きりたんを発話させる
import subprocess

# 英語で発話させる
from deep_translator import GoogleTranslator

@click.command()
@click.option("--model", default="base", help="Model to use", type=click.Choice(["tiny","base", "small","medium","large"]))
@click.option("--energy", default=300, help="Energy level for mic to detect", type=int)
@click.option("--dynamic_energy", default=False,is_flag=True, help="Flag to enable dynamic energy", type=bool)
@click.option("--pause", default=0.8, help="Pause time before entry ends", type=float)
def main(model, energy, pause,dynamic_energy):
    
    # 字幕設定（日本語）
    message_window_Ja = tk.Tk() 
    message_window_Ja.geometry('2160x150')
    message_window_Ja.title('ja')
    message_Ja = tk.Label(message_window_Ja, text="", font=("",45), anchor="center")
    message_Ja.pack()    
    
    # 設定（fine-tuning）
    audio_trained_queue = queue.Queue()
    result_queue = queue.Queue()
    
    processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3", language="Japanese", task="transcribe")
    # trained_model = WhisperForConditionalGeneration.from_pretrained("whisper_for_dominion").to('cuda')
    trained_model = WhisperForConditionalGeneration.from_pretrained("trained_model", ignore_mismatched_sizes=True).to('cuda')
    trained_model.config.max_target_positions = 1024
    trained_model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(language = "ja", task = "transcribe")
    trained_model.config.suppress_tokens = []
    
    # スレッドの実行
    threading.Thread(target=record_audio,
                     args=(audio_trained_queue, energy, pause, dynamic_energy)).start()
    threading.Thread(target=trained_transcribe_forever,
                     args=(audio_trained_queue, result_queue, processor, trained_model, message_Ja)).start()
    #threading.Thread(target=keyboard_detect).start()
                     
    # 字幕設定
    message_window_Ja.mainloop()
    
    # 出力設定
    while True:
        print(result_queue.get())
        
# 画像認識
import keyboard
import pyautogui
import easyocr
import re
import cv2

keyboard.on_press_key("z", lambda _:get_screen())
keyboard.on_press_key("c", lambda _:print("c"))

def get_screen():
    img_path = 'my_screenshot_all.png'

    # スクショを取る
    pyautogui.screenshot(img_path, region=(600,200,2350,1000))

    # 認識率を上げるためにグレースケールに変換
    img = cv2.imread(img_path)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(img_path, img_gray)
    
    # スクショからOCR実施、結果を返してもらう。
    reader = easyocr.Reader(['ja'])
    result = reader.readtext(img_path)

    prompt = ""
    for item in result:
        predicted_bbs=item[0] #4頂点の座標
        predicted_text=item[1] #認識したテキスト
        confident=item[2] #認識尤度

        # 不要な数字や記号を除去
        filtered_text = re.sub('[0-9]+|@|_|一|~|}|アタック','', predicted_text)
        if filtered_text != "" and len(prompt) < 300:

            # OCRの認識誤りを検査
            filtered_text = judge_distance(filtered_text)

            # 追加
            prompt = prompt + filtered_text + "、"

    # その他の汎用用語の追加
    prompt = prompt + "植民地、属州、公領、屋敷、白金貨、金貨、銀貨、銅貨、呪い、"
    prompt = prompt + "初手、2-5、5-2、3-4、4-3、9金、16金2購入、4金"

    print(prompt)

from Levenshtein import distance
def judge_distance(word_input):
    list = ["呪詛の山札","伝令官","石工","熟練工","収税吏","助言者","予言者","肉屋","広場","医者","商人ギルド","名品","パン屋","蝋燭職人","総督","取り壊し","サウナ","公使","囲郭村","王子","召喚","へそくり","船長","アヴァント","教会","闇市場","香辛料","星図","ギルド集会所","技術革新","悪巧み","研究","兵舎","発明家","増築","野外劇","国境警備隊","道路網","学園","悪党","貨物船","縁日","下水道","ランタン","司祭","実験","山村","パトロン","旗","剣客","王笏","角笛","山砦","鍵","輪作","サイロ","学者","絹商人","城門","資本主義","大聖堂","劇団","老魔女","根城","徴募官","ピアッツァ","出納官","運河","宝箱","彫刻家","ドゥカート金貨","先見者","旗手","艦隊","探査","追従者","廃坑","サー・マーチン","死の荷車","デイム・アンナ","共同墓地","サー・デストリー","はみだし者","襲撃者","ゴミあさり","建て直し","デイム・ジョセフィーヌ","サー・マイケル","救貧院","浮浪児","採集者","略奪","秘術師","隠遁者","生存者","偽造通貨","吟遊詩人","封土","廃村","物置","盗賊","浮浪者","従者","デイム・シルビア","屑屋","草茂る屋敷","略奪品","納屋","狂人","行進","デイム・ナタリー","図書館跡地","伯爵","サー・ヴァンデル","地下墓所","狂信者","デイム・モリー","賢者","物乞い","ネズミ","傭兵","青空市場","市場跡地","祭壇","山賊の宿営地","墓暴き","城塞","サー・ベイリー","金物商","武器庫","狩場","宿屋","番犬","官吏","織工","地図職人","進路","スーク","魔女の小屋","愚者の黄金","画策","遊牧民の野営地","街道","車大工","値切り屋","開発","交易人","坑道","大釜","遊牧民","大使館","よろずや","公爵夫人","狂戦士","辺境伯","国境の村","厩舎","神託","義賊","岐路","埋蔵金","香辛料商人","オアシス","不正利得","農地","シルクロード","牧羊犬","カエルの習性","賞金稼ぎ","リスの習性","ヤギ飼い","特価品","艀","炉","備蓄品","デストリエ","植民","村有緑地","鷹匠","パドック","苦労","門番","ドブネズミの習性","放逐","輸送","聖域","ラバの習性","追求","チョウの習性","要求","ラクダの隊列","カワウソの習性","黒猫","動物見本市","刈り入れ","増大","がらくた","カメレオンの習性","馬","商売","馬の習性","狩猟小屋","漁師","ラクダの習性","絶望","投資","暴走","遅延","ヤギの習性","貸し馬屋","馬丁","乗馬","行人","博打","強制退去","今を生きる","配給品","アザラシの習性","雄牛の習性","雪深い村","旅籠","モグラの習性","ミミズの習性","枢機卿","そり","ウミガメの習性","魔女の集会","サルの習性","首謀者","同盟","羊の習性","豚の習性","フクロウの習性","包領","騎兵隊","進軍","ハツカネズミの習性","外交官","拷問人","鉱山の村","改良","秘密の部屋","パトロール","貢物","願いの井戸","廷臣","交易場","風車","銅細工師","寵臣","仮面舞踏会","公爵","執事","身代わり","中庭","ハーレム","大広間","手先","隠し通路","破壊工作員","待ち伏せ","鉄工所","男爵","詐欺師","偵察員","共謀者","貴族","貧民街","橋","コルセア","原住民の村","停泊所","宝物庫","倉庫","商船","船着場","封鎖","海賊","漁村","前哨地","見張り","海図","密輸人","宝の地図","灯台","海の魔女","アストロラーベ","抑留","真珠採り","探検家","バザー","海賊船","大使","巾着切り","引揚水夫","潮溜り","サル","航海士","船乗り","隊商","島","幽霊船","海の妖婆","策士","木こり","魔女","密猟者","商人","宰相","市場","衛兵","玉座の間","屋敷","冒険者","祝祭","前駆者","祝宴","地下貯蔵庫","議事堂","家臣","役人","密偵","銀貨","公領","研究所","山賊","金貨","庭園","堀","呪い","書庫","銅貨","村","職人","民兵","鍛冶屋","改築","属州","鉱山","金貸し","泥棒","礼拝堂","工房","再建","豊穣の角笛","占い師","道化師","馬上槍試合","馬商人","金貨袋","狩猟団","村落","収穫","名馬","魔女娘","王冠","郎党","王女","農村","移動動物園","品評会","併合","凱旋門","宮殿","石","神殿","剣闘士","パトリキ","陣地","王城","技術者","庭師","宴会","大地への塩まき","大君主","徴税","峠","騒がしい村","壁","農家の市場","意外な授かり物","生贄","壮大な城","制圧","迷宮","公会堂","元手","凱旋","列柱","冠","塔","浴場","鹵獲品","ワイルドハント","戦車競走","博物館","資料庫","水道橋","征服","戦場","華やかな城","果樹園","山賊の砦","小さい城","砦","市街","儀式","粗末な城","御守り","掘進","女魔術師","広大な城","崩れた城","汚された神殿","墓標","軍団兵","オベリスク","投石機","狼の巣","幽霊城","結婚式","噴水","公共広場","大金","闘技場","エンポリウム","ヴィラ","開拓者","王室の鍛冶屋","昇進","寄付","リッチ","航海","堡塁","狩人","霊術師","輸入者","森の居住者","大工","メイソン団","触れ役","工芸家ギルド","沈没船の財宝","都市国家","穴居民","蹄鉄工","仲買人","戦闘計画","駐屯地","専門家","木工ギルド","宿屋の主人","追いはぎ","建築家ギルド","交換","占星術師団","市場の町","町","蛮族","薬草集め","粉屋","女予言者","高原の羊飼い","将軍","密使","歩哨","急使","すり師団","写本士の仲間たち","首都","山の民","銀行家連盟","ガレリア","遠い海岸","小売店主連盟","侯爵","射手","契約書","罠師の小屋","魔女の輪","侍祭","商人の野営地","領土","王家のガレー船","女魔導士","砂漠の案内人","発明家の家族","遊牧民団","散兵","古地図","改造","ギルドマスター","魔導士","ごますり","天幕","沿岸の避難港","下役","要塞","道化棒","平和的教団","島民","長老","生徒","植民地","香具師","司教","ティアラ","出資","造幣所","保管庫","収集品","大衆","山師","労働者の村","望楼","投機","隠し財産","大市場","ならず者","水晶球","鍛造","護符","禁制品","借金","交易路","銀行","都市","玉璽","石切場","有力者","行商人","拡張","書記","白金貨","記念碑","軍用金","金床","会計所","宮廷","失われし都市","相続","巨人","誘導","倒壊","案内人","雇人","カササギ","守銭奴","使節団","遺物","ウォリアー","騎士見習い","トレジャーハンター","門下生","農民","焚火","巡礼","使者","保存","教師","ワイン商","舞踏会","偵察隊","脱走兵","地下牢","語り部","探索","呪いの森","奇襲","鍛錬","複製","渡し船","魔除け","鼠取り","沼の妖婆","変容","兵士","探検","港町","遠隔地","掘出物","道具","移動遊園地","御料車","失われた技術","チャンピオン","施し","ヒーロー","隊商の護衛","橋の下のトロル","海路","山守","交易","法貨","立案","借入","工匠","呪われた金貨","悪魔祓い","悪人のアジト","月の恵み","夜襲","幽霊","ゴーストタウン","ウィル・オ・ウィスプ","憑依","みじめな生活","二重苦","森の恵み","風の恵み","ゾンビの石工","錯乱","牧草地","嫉妬","墓地","吸血鬼","夜警","貪欲","空の恵み","幻惑","レプラコーン","蝗害","田畑の恵み","ピクシー","コンクラーベ","愚者","疫病","守護者","戦争","願い","インプ","炎の恵み","太陽の恵み","羨望","幸運のコイン","聖なる木立ち","羊飼い","追跡者","暗躍者","修道院","呪われた村","カブラー","沼の恵み","大地の恵み","納骨堂","悲劇のヒーロー","忠犬","悪魔の工房","取り替え子","呪いの鏡","人狼","川の恵み","迫害者","偶像","恵みの村","ネクロマンサー","貧困","飢饉","森の迷子","詩人","凶兆","秘密の洞窟","コウモリ","生活苦","山の恵み","プーカ","海の恵み","ゾンビの弟子","ゾンビの密偵","革袋","ヤギ","ドルイド","魔法のランプ","恐怖","船首像","ロングシップ","呪われた","上陸部隊","ゴンドラ","縄","繁栄","沼地の小屋","キャビンボーイ","秘境の社","財産目当て","賞品のヤギ","工具","危難","尽きぬ杯","銀山","地図作り","内気な","檻","シャーマン","埋められた財宝","港の村","一等航海士","パズルボックス","友好的な","突貫","鏡映","小像","準備","切り裂き魔","疲れ知らずの","発進","乗組員","豊穣","回避","杖","鼓舞する","フリゲート船","勲章","現場監督","豊かな","調査","受け継がれた","岩屋","坩堝","旗艦","呪符の巻物","セイレーン","剣","六分儀","無謀な","戦利品の袋","せっかちな","略奪行為","宝珠","大渦巻","拡大","宝石","忍耐強い","運命の","侵略","鉱山道路","宝飾卵","アンフォラ","ダブロン金貨","襲撃","操舵手","価値ある村","密航者","巡礼者","盾","つるはし","ハンマー","埋葬","物色","へつらう","近隣の","配達","安価な","ペンダント","置き去り","敬虔な","旅行","トリックスター","王の隠し財産","錬金術師","薬草商","ブドウ園","念視の泉","大学","賢者の石","ポーション","使い魔","変成","薬師","ゴーレム","弟子","支配"]

    word_correct = word_input
    dist_min = 99
    for word_list in list:
        dist = distance(word_input, word_list)
        if dist < dist_min:
            print(word_input + ":" + word_correct + ":" + word_list)
            word_correct = word_list
            dist_min = dist
    return word_correct

# 録音処理
def record_audio(audio_trained_queue, energy, pause, dynamic_energy):
    #load the speech recognizer and set the initial energy threshold and pause threshold
    r = sr.Recognizer()
    r.energy_threshold = energy
    r.pause_threshold = pause
    r.dynamic_energy_threshold = dynamic_energy

    with sr.Microphone(sample_rate=16000) as source:
        print("Say something!")
        i = 0
        while True:
            # 録音（fine-tuning用)
            audio = r.listen(source)
            audio_trained_queue.put_nowait(audio.get_wav_data())
            
            i += 1

# 認識処理
def trained_transcribe_forever(audio_trained_queue, result_queue, processor, trained_model, message_Ja):
    while True:
        list = [audio_trained_queue.get()]
        
        common_voice = DatasetDict()
        common_voice["train"] = Dataset.from_dict({"audio": list}).cast_column("audio", Audio(sampling_rate=16000))
            
        for i in range(len(common_voice["train"])):

            # プロンプトの準備
            prompt_ids = processor.get_prompt_ids(prompt)
                        
            # 音声データの準備
            inputs = processor(common_voice["train"][i]["audio"]["array"], return_tensors="pt", sampling_rate=16000).to('cuda')
            input_features = inputs.input_features

            try:
                # 認識実行
                generated_ids = trained_model.generate(inputs=input_features, max_new_tokens=512, prompt_ids=prompt_ids)
                # transcription = processor.batch_decode(generated_ids, skip_special_tokens=True, beam_size=10)[0]
                transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

                # プロンプトを除去
                filtered_transcription = re.sub(prompt,'', transcription)
                
                # 誤認識の検査（未採用）
                # filtered_transcription = judge_distance_transcription(filtered_transcription)

                # 表示処理
                result_queue.put_nowait(filtered_transcription)
                makeOutput(message_Ja, filtered_transcription)
                print(filtered_transcription)
            
                # Google翻訳
                # predicted_text_En = GoogleTranslator(source='auto',target='en').translate(transcription)
                # result_queue.put_nowait("Google翻訳: " + predicted_text_En)
            except Exception as e:
                print(e)

# 誤認識の検査
# Whisperの認識結果について誤認識を検出して正しい語へ変換し直す処理
# 音声認識結果をひらがなに変換してドミニオン全カード名と総当たりで突き合わせて
# 閾値より高い＆最も値の大きい語に変換する
def judge_distance_transcription(transcription):
    list = {"伝令官":"でんれいかん","石工":"いしく","熟練工":"じゅくれんこう","収税吏":"しゅうぜいり","助言者":"じょげんしゃ","予言者":"よげんしゃ","肉屋":"にくや","広場":"ひろば","医者":"いしゃ","商人ギルド":"しょうにんぎるど","名品":"めいひん","パン屋":"ぱんや","蝋燭職人":"ろうそくしょくにん","総督":"そうとく","取り壊し":"とりこわし","サウナ":"さうな","公使":"こうし","囲郭村":"いかくそん","王子":"おうじ","召喚":"しょうかん","へそくり":"へそくり","船長":"せんちょう","アヴァント":"あう゛ぁんと","教会":"きょうかい","闇市場":"やみいちば","香辛料":"こうしんりょう","星図":"せいず","ギルド集会所":"ぎるどしゅうかいじょ","技術革新":"ぎじゅつかくしん","悪巧み":"わるだくみ","研究":"けんきゅう","兵舎":"へいしゃ","発明家":"はつめいか","増築":"ぞうちく","野外劇":"やがいげき","国境警備隊":"こっきょうけいびたい","道路網":"どうろもう","学園":"がくえん","悪党":"あくとう","貨物船":"かもつせん","縁日":"えんにち","下水道":"げすいどう","ランタン":"らんたん","司祭":"しさい","実験":"じっけん","山村":"さんそん","パトロン":"ぱとろん","旗":"はた","剣客":"けんかく","王笏":"おうしゃく","角笛":"つのぶえ","山砦":"さんさい","鍵":"かぎ","輪作":"りんさく","サイロ":"さいろ","学者":"がくしゃ","絹商人":"きぬしょうにん","城門":"じょうもん","資本主義":"しほんしゅぎ","大聖堂":"だいせいどう","劇団":"げきだん","老魔女":"ろうまじょ","根城":"ねじろ","徴募官":"ちょうぼかん","ピアッツァ":"ぴあっつぁ","出納官":"すいとうかん","運河":"うんが","宝箱":"たからばこ","彫刻家":"ちょうこくか","ドゥカート金貨":"どぅかーときんか","先見者":"せんけんしゃ","旗手":"きしゅ","艦隊":"かんたい","探査":"たんさ","追従者":"ついじゅうしゃ","廃坑":"はいこう","サー・マーチン":"さー・まーちん","死の荷車":"しのにぐるま","デイム・アンナ":"でいむ・あんな","共同墓地":"きょうどうぼち","サー・デストリー":"さー・ですとりー","はみだし者":"はみだしもの","襲撃者":"しゅうげきしゃ","ゴミあさり":"ごみあさり","建て直し":"たてなおし","デイム・ジョセフィーヌ":"でいむ・じょせふぃーぬ","サー・マイケル":"さー・まいける","救貧院":"きゅうひんいん","浮浪児":"ふろうじ","採集者":"さいしゅうしゃ","略奪":"りゃくだつ","秘術師":"ひじゅつし","隠遁者":"いんとんしゃ","生存者":"せいぞんしゃ","偽造通貨":"ぎぞうつうか","吟遊詩人":"ぎんゆうしじん","封土":"ほうど","廃村":"はいそん","物置":"ものおき","盗賊":"とうぞく","浮浪者":"ふろうしゃ","従者":"じゅうしゃ","デイム・シルビア":"でいむ・しるびあ","屑屋":"くずや","草茂る屋敷":"くさしげるやしき","略奪品":"りゃくだつひん","納屋":"なや","狂人":"きょうじん","行進":"こうしん","デイム・ナタリー":"でいむ・なたりー","図書館跡地":"としょかんあとち","伯爵":"はくしゃく","サー・ヴァンデル":"さー・う゛ぁんでる","地下墓所":"ちかぼしょ","狂信者":"きょうしんしゃ","デイム・モリー":"でいむ・もりー","賢者":"けんじゃ","物乞い":"ものごい","ネズミ":"ねずみ","傭兵":"ようへい","青空市場":"あおぞらいちば","市場跡地":"いちばあとち","祭壇":"さいだん","山賊の宿営地":"さんぞくのしゅくえいち","墓暴き":"はかあばき","城塞":"じょうさい","サー・ベイリー":"さー・べいりー","金物商":"かなものしょう","武器庫":"ぶきこ","狩場":"かりば","宿屋":"やどや","番犬":"ばんけん","官吏":"かんり","織工":"しょっこう","地図職人":"ちずしょくにん","進路":"しんろ","スーク":"すーく","魔女の小屋":"まじょのこや","愚者の黄金":"ぐしゃのおうごん","画策":"かくさく","遊牧民の野営地":"ゆうぼくみんのやえいち","街道":"かいどう","車大工":"くるまだいく","値切り屋":"ねぎりや","開発":"かいはつ","交易人":"こうえきにん","坑道":"こうどう","大釜":"おおがま","遊牧民":"ゆうぼくみん","大使館":"たいしかん","よろずや":"よろずや","公爵夫人":"こうしゃくふじん","狂戦士":"きょうせんし","辺境伯":"へんきょうはく","国境の村":"こっきょうのむら","厩舎":"きゅうしゃ","神託":"しんたく","義賊":"ぎぞく","岐路":"きろ","埋蔵金":"まいぞうきん","香辛料商人":"こうしんりょうしょうにん","オアシス":"おあしす","不正利得":"ふせいりとく","農地":"のうち","シルクロード":"しるくろーど","牧羊犬":"ぼくようけん","カエルの習性":"かえるのしゅうせい","賞金稼ぎ":"しょうきんかせぎ","リスの習性":"りすのしゅうせい","ヤギ飼い":"やぎかい","特価品":"とっかひん","艀":"はしけ","炉":"ろ","備蓄品":"びちくひん","デストリエ":"ですとりえ","植民":"しょくみん","村有緑地":"そんゆうりょくち","鷹匠":"たかじょう","パドック":"ぱどっく","苦労":"くろう","門番":"もんばん","ドブネズミの習性":"どぶねずみのしゅうせい","放逐":"ほうちく","輸送":"ゆそう","聖域":"せいいき","ラバの習性":"らばのしゅうせい","追求":"ついきゅう","チョウの習性":"ちょうのしゅうせい","要求":"ようきゅう","ラクダの隊列":"らくだのたいれつ","カワウソの習性":"かわうそのしゅうせい","黒猫":"くろねこ","動物見本市":"どうぶつみほんいち","刈り入れ":"かりいれ","増大":"ぞうだい","がらくた":"がらくた","カメレオンの習性":"かめれおんのしゅうせい","馬":"うま","商売":"しょうばい","馬の習性":"うまのしゅうせい","狩猟小屋":"しゅりょうごや","漁師":"りょうし","ラクダの習性":"らくだのしゅうせい","絶望":"ぜつぼう","投資":"とうし","暴走":"ぼうそう","遅延":"ちえん","ヤギの習性":"やぎのしゅうせい","貸し馬屋":"かしうまや","馬丁":"ばてい","乗馬":"じょうば","行人":"こうじん","博打":"ばくち","強制退去":"きょうせいたいきょ","今を生きる":"いまをいきる","配給品":"はいきゅうひん","アザラシの習性":"あざらしのしゅうせい","雄牛の習性":"おうしのしゅうせい","雪深い村":"ゆきぶかいむら","旅籠":"はたご","モグラの習性":"もぐらのしゅうせい","ミミズの習性":"みみずのしゅうせい","枢機卿":"すうききょう","そり":"そり","ウミガメの習性":"うみがめのしゅうせい","魔女の集会":"まじょのしゅうかい","サルの習性":"さるのしゅうせい","首謀者":"しゅぼうしゃ","同盟":"どうめい","羊の習性":"ひつじのしゅうせい","豚の習性":"ぶたのしゅうせい","フクロウの習性":"ふくろうのしゅうせい","包領":"ほうりょう","騎兵隊":"きへいたい","進軍":"しんぐん","ハツカネズミの習性":"はつかねずみのしゅうせい","外交官":"がいこうかん","拷問人":"ごうもんにん","鉱山の村":"こうざんのむら","改良":"かいりょう","秘密の部屋":"ひみつのへや","パトロール":"ぱとろーる","貢物":"みつぎもの","願いの井戸":"ねがいのいど","廷臣":"ていしん","交易場":"こうえきじょう","風車":"ふうしゃ","銅細工師":"どうざいくし","寵臣":"ちょうしん","仮面舞踏会":"かめんぶとうかい","公爵":"こうしゃく","執事":"しつじ","身代わり":"みがわり","中庭":"なかにわ","ハーレム":"はーれむ","大広間":"おおひろま","手先":"てさき","隠し通路":"かくしつうろ","破壊工作員":"はかいこうさくいん","待ち伏せ":"まちぶせ","鉄工所":"てっこうじょ","男爵":"だんしゃく","詐欺師":"さぎし","偵察員":"ていさついん","共謀者":"きょうぼうしゃ","貴族":"きぞく","貧民街":"ひんみんがい","橋":"はし","コルセア":"こるせあ","原住民の村":"げんじゅうみんのむら","停泊所":"ていはくじょ","宝物庫":"ほうもつこ","倉庫":"そうこ","商船":"しょうせん","船着場":"ふなつきば","封鎖":"ふうさ","海賊":"かいぞく","漁村":"ぎょそん","前哨地":"ぜんしょうち","見張り":"みはり","海図":"かいず","密輸人":"みつゆにん","宝の地図":"たからのちず","灯台":"とうだい","海の魔女":"うみのまじょ","アストロラーベ":"あすとろらーべ","抑留":"よくりゅう","真珠採り":"しんじゅとり","探検家":"たんけんか","バザー":"ばざー","海賊船":"かいぞくせん","大使":"たいし","巾着切り":"きんちゃくきり","引揚水夫":"ひきあげすいふ","潮溜り":"しおだまり","サル":"さる","航海士":"こうかいし","船乗り":"ふなのり","隊商":"たいしょう","島":"しま","幽霊船":"ゆうれいせん","海の妖婆":"うみのようば","策士":"さくし","木こり":"きこり","魔女":"まじょ","密猟者":"みつりょうしゃ","商人":"しょうにん","宰相":"さいしょう","市場":"いちば","衛兵":"えいへい","玉座の間":"ぎょくざのま","屋敷":"やしき","冒険者":"ぼうけんしゃ","祝祭":"しゅくさい","前駆者":"ぜんくしゃ","祝宴":"しゅくえん","地下貯蔵庫":"ちかちょぞうこ","議事堂":"ぎじどう","家臣":"かしん","役人":"やくにん","密偵":"みってい","銀貨":"ぎんか","公領":"こうりょう","研究所":"けんきゅうじょ","山賊":"さんぞく","金貨":"きんか","庭園":"ていえん","堀":"ほり","呪い":"のろい","書庫":"しょこ","銅貨":"どうか","村":"むら","職人":"しょくにん","民兵":"みんぺい","鍛冶屋":"かじや","改築":"かいちく","属州":"ぞくしゅう","鉱山":"こうざん","金貸し":"かねかし","泥棒":"どろぼう","礼拝堂":"れいはいどう","工房":"こうぼう","再建":"さいけん","豊穣の角笛":"ほうじょうのつのぶえ","占い師":"うらないし","道化師":"どうけし","馬上槍試合":"ばじょうやりじあい","馬商人":"うましょうにん","金貨袋":"きんかぶくろ","狩猟団":"しゅりょうだん","村落":"そんらく","収穫":"しゅうかく","名馬":"めいば","魔女娘":"まじょむすめ","王冠":"おうかん","郎党":"ろうとう","王女":"おうじょ","農村":"のうそん","移動動物園":"いどうどうぶつえん","品評会":"ひんぴょうかい","併合":"へいごう","凱旋門":"がいせんもん","宮殿":"きゅうでん","石":"いし","神殿":"しんでん","剣闘士":"けんとうし","パトリキ":"ぱとりき","陣地":"じんち","王城":"おうじょう","技術者":"ぎじゅつしゃ","庭師":"にわし","宴会":"えんかい","大地への塩まき":"だいちへのしおまき","大君主":"だいくんしゅ","徴税":"ちょうぜい","峠":"とうげ","騒がしい村":"さわがしいむら","壁":"かべ","農家の市場":"のうかのいちば","意外な授かり物":"いがいなさずかりもの","生贄":"いけにえ","壮大な城":"そうだいなしろ","制圧":"せいあつ","迷宮":"めいきゅう","公会堂":"こうかいどう","元手":"もとで","凱旋":"がいせん","列柱":"れっちゅう","冠":"かんむり","塔":"とう","浴場":"よくじょう","鹵獲品":"ろかくひん","ワイルドハント":"わいるどはんと","戦車競走":"せんしゃきょうそう","博物館":"はくぶつかん","資料庫":"しりょうこ","水道橋":"すいどうきょう","征服":"せいふく","戦場":"せんじょう","華やかな城":"はなやかなしろ","果樹園":"かじゅえん","山賊の砦":"さんぞくのとりで","小さい城":"ちいさいしろ","砦":"とりで","市街":"しがい","儀式":"ぎしき","粗末な城":"そまつなしろ","御守り":"おまもり","掘進":"くっしん","女魔術師":"おんなまじゅつし","広大な城":"こうだいなしろ","崩れた城":"くずれたしろ","汚された神殿":"けがされたしんでん","墓標":"ぼひょう","軍団兵":"ぐんだんへい","オベリスク":"おべりすく","投石機":"とうせきき","狼の巣":"おおかみのす","幽霊城":"ゆうれいじょう","結婚式":"けっこんしき","噴水":"ふんすい","公共広場":"こうきょうひろば","大金":"たいきん","闘技場":"とうぎじょう","エンポリウム":"えんぽりうむ","ヴィラ":"う゛ぃら","開拓者":"かいたくしゃ","王室の鍛冶屋":"おうしつのかじや","昇進":"しょうしん","寄付":"きふ","リッチ":"りっち","航海":"こうかい","堡塁":"ほうるい","狩人":"かりうど","霊術師":"れいじゅつし","輸入者":"ゆにゅうしゃ","森の居住者":"もりのきょじゅうしゃ","大工":"だいく","メイソン団":"めいそんだん","触れ役":"ふれやく","工芸家ギルド":"こうげいかぎるど","沈没船の財宝":"ちんぼつせんのざいほう","都市国家":"としこっか","穴居民":"けっきょみん","蹄鉄工":"ていてつこう","仲買人":"なかがいにん","戦闘計画":"せんとうけいかく","駐屯地":"ちゅうとんち","専門家":"せんもんか","木工ギルド":"もっこうぎるど","宿屋の主人":"やどやのしゅじん","追いはぎ":"おいはぎ","建築家ギルド":"けんちくかぎるど","交換":"こうかん","占星術師団":"せんせいじゅつしだん","市場の町":"しじょうのまち","町":"まち","蛮族":"ばんぞく","薬草集め":"やくそうあつめ","粉屋":"こなや","女予言者":"おんなよげんしゃ","高原の羊飼い":"こうげんのひつじかい","将軍":"しょうぐん","密使":"みっし","歩哨":"ほしょう","急使":"きゅうし","すり師団":"すりしだん","写本士の仲間たち":"しゃほんしのなかまたち","首都":"しゅと","山の民":"やまのたみ","銀行家連盟":"ぎんこうかれんめい","ガレリア":"がれりあ","遠い海岸":"とおいかいがん","小売店主連盟":"こうりてんしゅれんめい","侯爵":"こうしゃく","射手":"しゃしゅ","契約書":"けいやくしょ","罠師の小屋":"わなしのこや","魔女の輪":"まじょのわ","侍祭":"じさい","商人の野営地":"しょうにんのやえいち","領土":"りょうど","王家のガレー船":"おうけのがれーせん","女魔導士":"おんなまどうし","砂漠の案内人":"さばくのあんないにん","発明家の家族":"はつめいかのかぞく","遊牧民団":"ゆうぼくみんだん","散兵":"さんぺい","古地図":"こちず","改造":"かいぞう","ギルドマスター":"ぎるどますたー","魔導士":"まどうし","ごますり":"ごますり","天幕":"てんまく","沿岸の避難港":"えんがんのひなんこう","下役":"したやく","要塞":"ようさい","道化棒":"どうけぼう","平和的教団":"へいわてききょうだん","島民":"とうみん","長老":"ちょうろう","生徒":"せいと","植民地":"しょくみんち","香具師":"やし","司教":"しきょう","ティアラ":"てぃあら","出資":"しゅっし","造幣所":"ぞうへいしょ","保管庫":"ほかんこ","収集品":"しゅうしゅうひん","大衆":"たいしゅう","山師":"やまし","労働者の村":"ろうどうしゃのむら","望楼":"ぼうろう","投機":"とうき","隠し財産":"かくしざいさん","大市場":"おおいちば","ならず者":"ならずもの","水晶球":"すいしょうだま","鍛造":"たんぞう","護符":"ごふ","禁制品":"きんせいひん","借金":"しゃっきん","交易路":"こうえきろ","銀行":"ぎんこう","都市":"とし","玉璽":"ぎょくじ","石切場":"いしきりば","有力者":"ゆうりょくしゃ","行商人":"ぎょうしょうにん","拡張":"かくちょう","書記":"しょき","白金貨":"はくきんか","記念碑":"きねんひ","軍用金":"ぐんようきん","金床":"かなとこ","会計所":"かいけいしょ","宮廷":"きゅうてい","失われし都市":"うしなわれしとし","相続":"そうぞく","巨人":"きょじん","誘導":"ゆうどう","倒壊":"とうかい","案内人":"あんないにん","雇人":"やといにん","カササギ":"かささぎ","守銭奴":"しゅせんど","使節団":"しせつだん","遺物":"いぶつ","ウォリアー":"うぉりあー","騎士見習い":"きしみならい","トレジャーハンター":"とれじゃーはんたー","門下生":"もんかせい","農民":"のうみん","焚火":"たきび","巡礼":"じゅんれい","使者":"ししゃ","保存":"ほぞん","教師":"きょうし","ワイン商":"わいんしょう","舞踏会":"ぶとうかい","偵察隊":"ていさつたい","脱走兵":"だっそうへい","地下牢":"ちかろう","語り部":"かたりべ","探索":"たんさく","呪いの森":"のろいのもり","奇襲":"きしゅう","鍛錬":"たんれん","複製":"ふくせい","渡し船":"わたしぶね","魔除け":"まよけ","鼠取り":"ねずみとり","沼の妖婆":"ぬまのようば","変容":"へんよう","兵士":"へいし","探検":"たんけん","港町":"みなとまち","遠隔地":"えんかくち","掘出物":"ほりだしもの","道具":"どうぐ","移動遊園地":"いどうゆうえんち","御料車":"ごりょうしゃ","失われた技術":"うしなわれたぎじゅつ","チャンピオン":"ちゃんぴおん","施し":"ほどこし","ヒーロー":"ひーろー","隊商の護衛":"たいしょうのごえい","橋の下のトロル":"はしのしたのとろる","海路":"かいろ","山守":"やまもり","交易":"こうえき","法貨":"ほうか","立案":"りつあん","借入":"しゃくにゅう","工匠":"こうしょう","呪われた金貨":"のろわれたきんか","悪魔祓い":"あくまばらい","悪人のアジト":"あくにんのあじと","月の恵み":"つきのめぐみ","夜襲":"やしゅう","幽霊":"ゆうれい","ゴーストタウン":"ごーすとたうん","ウィル・オ・ウィスプ":"うぃる・お・うぃすぷ","憑依":"ひょうい","みじめな生活":"みじめなせいかつ","二重苦":"にじゅうく","森の恵み":"もりのめぐみ","風の恵み":"かぜのめぐみ","ゾンビの石工":"ぞんびのいしく","錯乱":"さくらん","牧草地":"ぼくそうち","嫉妬":"しっと","墓地":"ぼち","吸血鬼":"きゅうけつき","夜警":"やけい","貪欲":"どんよく","空の恵み":"そらのめぐみ","幻惑":"げんわく","レプラコーン":"れぷらこーん","蝗害":"こうがい","田畑の恵み":"たはたのめぐみ","ピクシー":"ぴくしー","コンクラーベ":"こんくらーべ","愚者":"ぐしゃ","疫病":"えきびょう","守護者":"しゅごしゃ","戦争":"せんそう","願い":"ねがい","インプ":"いんぷ","炎の恵み":"ほのおのめぐみ","太陽の恵み":"たいようのめぐみ","羨望":"せんぼう","幸運のコイン":"こううんのこいん","聖なる木立ち":"せいなるこだち","羊飼い":"ひつじかい","追跡者":"ついせきしゃ","暗躍者":"あんやくしゃ","修道院":"しゅうどういん","呪われた村":"のろわれたむら","カブラー":"かぶらー","沼の恵み":"ぬまのめぐみ","大地の恵み":"だいちのめぐみ","納骨堂":"のうこつどう","悲劇のヒーロー":"ひげきのひーろー","忠犬":"ちゅうけん","悪魔の工房":"あくまのこうぼう","取り替え子":"とりかえこ","呪いの鏡":"のろいのかがみ","人狼":"じんろう","川の恵み":"かわのめぐみ","迫害者":"はくがいしゃ","偶像":"ぐうぞう","恵みの村":"めぐみのむら","ネクロマンサー":"ねくろまんさー","貧困":"ひんこん","飢饉":"ききん","森の迷子":"もりのまいご","詩人":"しじん","凶兆":"きょうちょう","秘密の洞窟":"ひみつのどうくつ","コウモリ":"こうもり","生活苦":"せいかつく","山の恵み":"やまのめぐみ","プーカ":"ぷーか","海の恵み":"うみのめぐみ","ゾンビの弟子":"ぞんびのでし","ゾンビの密偵":"ぞんびのみってい","革袋":"かわぶくろ","ヤギ":"やぎ","ドルイド":"どるいど","魔法のランプ":"まほうのらんぷ","恐怖":"きょうふ","船首像":"せんしゅぞう","ロングシップ":"ろんぐしっぷ","呪われた":"のろわれた","上陸部隊":"じょうりくぶたい","ゴンドラ":"ごんどら","縄":"なわ","繁栄":"はんえい","沼地の小屋":"ぬまちのこや","キャビンボーイ":"きゃびんぼーい","秘境の社":"ひきょうのやしろ","財産目当て":"ざいさんめあて","賞品のヤギ":"しょうひんのやぎ","工具":"こうぐ","危難":"きなん","尽きぬ杯":"つきぬさかずき","銀山":"ぎんざん","地図作り":"ちずづくり","内気な":"うちきな","檻":"おり","シャーマン":"しゃーまん","埋められた財宝":"うめられたざいほう","港の村":"みなとのむら","一等航海士":"いっとうこうかいし","パズルボックス":"ぱずるぼっくす","友好的な":"ゆうこうてきな","突貫":"とっかん","鏡映":"きょうえい","小像":"しょうぞう","準備":"じゅんび","切り裂き魔":"きりさきま","疲れ知らずの":"つかれしらずの","発進":"はっしん","乗組員":"のりくみいん","豊穣":"ほうじょう","回避":"かいひ","杖":"つえ","鼓舞する":"こぶする","フリゲート船":"ふりげーとせん","勲章":"くんしょう","現場監督":"げんばかんとく","豊かな":"ゆたかな","調査":"ちょうさ","受け継がれた":"うけつがれた","岩屋":"いわや","坩堝":"るつぼ","旗艦":"きかん","呪符の巻物":"じゅふのまきもの","セイレーン":"せいれーん","剣":"けん","六分儀":"ろくぶんぎ","無謀な":"むぼうな","戦利品の袋":"せんりひんのふくろ","せっかちな":"せっかちな","略奪行為":"りゃくだつこうい","宝珠":"ほうじゅ","大渦巻":"おおうずまき","拡大":"かくだい","宝石":"ほうせき","忍耐強い":"にんたいづよい","運命の":"うんめいの","侵略":"しんりゃく","鉱山道路":"こうざんどうろ","宝飾卵":"ほうしょくらん","アンフォラ":"あんふぉら","ダブロン金貨":"だぶろんきんか","襲撃":"しゅうげき","操舵手":"そうだしゅ","価値ある村":"かちあるむら","密航者":"みっこうしゃ","巡礼者":"じゅんれいしゃ","盾":"たて","つるはし":"つるはし","ハンマー":"はんまー","埋葬":"まいそう","物色":"ぶっしょく","へつらう":"へつらう","近隣の":"きんりんの","配達":"はいたつ","安価な":"あんかな","ペンダント":"ぺんだんと","置き去り":"おきざり","敬虔な":"けいけんな","旅行":"りょこう","トリックスター":"とりっくすたー","王の隠し財産":"おうのかくしざいさん","錬金術師":"れんきんじゅつし","薬草商":"やくそうしょう","ブドウ園":"ぶどうえん","念視の泉":"ねんしのいずみ","大学":"だいがく","賢者の石":"けんじゃのいし","ポーション":"ぽーしょん","使い魔":"つかいま","変成":"へんせい","薬師":"くすし","ゴーレム":"ごーれむ","弟子":"でし","支配":"しはい"}

    word_gen = transcription

    word_correct = word_gen
    
    furigana = ""
    result = kakasi.convert(word_gen)

    for item in result:
        furigana = furigana + item['hira'].capitalize()

    word_len = len(furigana)
    
    dist_min = 0
    for key, value in list.items():
        dist = word_len / ( word_len + distance(furigana, value) - 1 )
        if dist_min < dist and 0.8 < dist:
            word_correct = key
            dist_min = dist
            # print(furigana + ":" + word_correct + ":" + value + ":" + str(dist))
    
    return_transcription = re.sub(word_gen, word_correct, transcription)
    print(transcription + ":" + return_transcription)
    
    return return_transcription

# 認識結果をウィンドウに表示する処理
# 音声認識でたまに発生する誤認識（はじめしゃちょーとか）のフィルタもする
# 認識結果が誤認識であった場合は発言せず終了する
import re
from pykakasi import kakasi
kakasi = kakasi()

def makeOutput(message_Ja, transcription):
    ng_words =  \
    'ご視聴ありがとうございました' \
    '|いただきます'\
    '|はじめしゃちょー'\
    '|エンディング'\
    '|\\('\
    '|（'\
    
    # print("フィルタ前" + transcription)
    if not re.findall(ng_words, transcription) and len(transcription) < 50:
        
        if len(transcription) < 15:
            message_Ja.configure(font=("",45))
        elif len(transcription) < 25:
            message_Ja.configure(font=("",35))
        else:
            message_Ja.configure(font=("",25))

        message_Ja["text"] =  transcription # ウィンドウに表示
        #subprocess.run("seikasay2 -cid 1707 -t " + transcription) # きりたん発話
        
main()
