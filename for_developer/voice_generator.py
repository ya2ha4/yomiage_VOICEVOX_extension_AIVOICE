import os
import json
from abc import ABCMeta, abstractmethod
from for_developer.discordbot_setting import *
from for_developer.voice_speaker import AbstractVoiceSpeaker, VoiceVoxVoiceSpeaker

class AbstractVoiceGenerator(metaclass=ABCMeta):
    @abstractmethod
    def generate(self, character_name:str, style_name:str, message:str, speed:float):
        raise NotImplementedError()

    @abstractmethod
    def getSpeakersStr(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def hasSpeaker(self, name) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def getSpeaker(self, name) -> AbstractVoiceSpeaker:
        raise NotImplementedError
    
    @abstractmethod
    def hasStyle(self, speaker_name, style_name) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def getName(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def getSpeakersDict(self) -> dict:
        raise NotImplementedError
    
class VoiceVoxVoiceGenerator(AbstractVoiceGenerator):
    def __init__(self, name:str, port:str):
        # インスタンス変数の指定
        self.name = name
        self.port = port
        self.speakers = {}

        try:
            # VOICEVOX（あるいは互換ソフト）から、話者の一覧をJsonで取得する
            command = bat_speakers + ' ' + port
            os.system(command)

            #Jsonを解析して話者の情報を動的に取得する
            print("Jsonの解析開始")
            with open('tmp/speakers.json', 'r', encoding="utf-8_sig") as json_open:
                json_load = json.load(json_open)
                for speaker in json_load:
                    speaker_name = speaker['name']
                    speaker_styles = speaker['styles']
                    style_dict = {}

                    for style in speaker_styles:
                        style_dict[style['name']] = int(style['id'])
                    self.speakers[speaker_name] = VoiceVoxVoiceSpeaker(speaker_name, style_dict)

            print("Jsonの解析完了")
            print(self.getSpeakersStr())
        except Exception as e:
            raise e
            
    def generate(self, character_name:str, style_name:str, message:str, parameter:dict):

        # チャットの内容をutf-8でエンコードする
        text = message.encode('utf-8')

        # HTTP POSTで投げられるように形式を変える
        query = ''
        for item in text:
            query += '%'
            query += hex(item)[2:].upper()

        # コマンドの設定
        style_id_str = str(self.speakers[character_name].getStyleId(style_name))
        command1 = bat_json + ' ' + self.port + ' ' + query + ' ' + style_id_str
        command2 = bat_voice + ' ' + self.port + ' ' + style_id_str

        # リクエスト用Jsonの生成
        os.system(command1)

        # jsonファイルのかきかえ
        with open(json_file, encoding="utf-8") as f:
            data_lines = f.read()
            data_lines = data_lines.replace('"speedScale":1.0'     , '"speedScale":'     +str(parameter["speed"]))
            data_lines = data_lines.replace('"pitchScale":0.0'     , '"pitchScale":'     +str(parameter["pitch"]))
            data_lines = data_lines.replace('"intonationScale":1.0', '"intonationScale":'+str(parameter["intonation"]))
            data_lines = data_lines.replace('"volumeScale":1.0'    , '"volumeScale":'    +str(parameter["volume"]))
        # 同じファイル名で保存
        with open(json_file, mode="w", encoding="utf-8") as f:
            f.write(data_lines)

        # wavファイルの生成
        os.system(command2)
    
    def getSpeakersStr(self) -> str:
        ret = "【" + self.name + "】\n"
        
        for speaker_name in self.speakers:
            ret += self.speakers[speaker_name].getStylesStr() + "\n"
        
        return ret
    
    def hasSpeaker(self, name) -> bool:
        if name in self.speakers.keys():
            return True
        else:
            return False
    
    def getSpeaker(self, name) -> VoiceVoxVoiceSpeaker:
        return self.speakers[name]
    
    def hasStyle(self, speaker_name, style_name) -> bool:
        if self.hasSpeaker(speaker_name):
            speaker = self.speakers[speaker_name]
            if speaker.hasStyle(style_name):
                return True
        
        return False
    
    def getName(self) -> str:
        return self.name
    
    def getSpeakerWithStyleId(self, id:int) -> VoiceVoxVoiceSpeaker:
        for speaker in self.speakers.values():
            if speaker.hasStyleId(id):
                return speaker
        return None
    
    def getSpeakersDict(self) -> dict:
        return self.speakers


# using: https://gist.github.com/mushroom080/5f219c8c981b6297fb238c55742d8114
import os
import clr

class AiVoiceVoiceGenerator(AbstractVoiceGenerator):
    def __init__(self, name:str, port:str):
        # インスタンス変数の指定
        self.name = name
        self.port = port
        self.speakers = {}

        self.tmp_dir = f'tmp/{name}'
        self.is_enable = False
        self.tts_control = None

        # A.I.Voice Editor 存在チェック
        self.editor_dir = os.environ['ProgramW6432'] + "\\AI\\AIVoice\\AIVoiceEditor\\"
        if not os.path.isfile(self.editor_dir + "AI.Talk.Editor.Api.dll"):
            print("A.I.VOICE Editor API を利用する為に必要なファイルがインストールされていません。")
            print("A.I.VOICE Editor (v1.3.0以降) をインストールして下さい。")
            return

        try:
            # pythonnet DLLの読み込み
            clr.AddReference(self.editor_dir + "AI.Talk.Editor.Api")
            from AI.Talk.Editor.Api import TtsControl, HostStatus
            self.tts_control = TtsControl()

            # A.I.VOICE Editor APIの初期化
            host_name = self.tts_control.GetAvailableHostNames()[0]
            self.tts_control.Initialize(host_name)

            # A.I.VOICE（あるいは互換ソフト）から、話者の一覧をJsonで取得する
            ## todo: TtsControl.VoiceNames, GetListVoicePreset などで対応
            ## 現在は self.tmp_dir 直下に speaekrs.json を手動で作成し配置しています

            #Jsonを解析して話者の情報を動的に取得する
            print("Jsonの解析開始")
            with open(f'{self.tmp_dir}/speakers.json', 'r', encoding="utf-8_sig") as json_open:
                json_load = json.load(json_open)
                for speaker in json_load:
                    speaker_name = speaker['name']
                    speaker_styles = speaker['styles']
                    style_dict = {}

                    for style in speaker_styles:
                        style_dict[style['name']] = int(style['id'])
                    self.speakers[speaker_name] = VoiceVoxVoiceSpeaker(speaker_name, style_dict)

            print("Jsonの解析完了")
            print(self.getSpeakersStr())

            # A.I.VOICE Editorの起動
            if self.tts_control.Status == HostStatus.NotRunning:
                self.tts_control.StartHost()

            # A.I.VOICE Editorへ接続確認
            self.tts_control.Connect()
            host_version = self.tts_control.Version
            print(f"{host_name} (v{host_version}) へ接続しました。")
            self.tts_control.Disconnect()

            self.is_enable = True

        except Exception as e:
            raise e

    def generate(self, character_name:str, style_name:str, message:str, parameter:dict):
        if not self.is_enable:
            print("初期設定時に問題があった為、wav生成は実行しません。")
            return

        # Editorの起動確認
        from AI.Talk.Editor.Api import HostStatus
        if self.tts_control.Status == HostStatus.NotRunning:
            self.tts_control.StartHost()

        self.tts_control.Connect()

        ## todo: parameter を TtsControl のプリセットボイスに反映
        ## TtsControl.SetVoicePreset() で反映

        ## rem: 事前にA.I.VOICE Editor 側で「キャラ名_スタイル名」のプリセットボイスを用意してそれを使用することに
        ## 例：「結月ゆかり_ノーマル」「結月ゆかり_雫」「紲星あかり_ノーマル」「紲星あかり_蕾」
        ## 注：プリセットボイス追加した際、苗字と名前の間にあるスペースを消して設定すること
        ## プリセットボイスを追加したら tmp/AIVOICE/speakers.json に追加
        print(f"{character_name}_{style_name}")
        self.tts_control.CurrentVoicePresetName = f"{character_name}_{style_name}"

        # テキストを設定
        self.tts_control.Text = message

        # wavファイルの生成
        self.tts_control.SaveAudioToFile(voice_file)

        self.tts_control.Disconnect()
    
    def getSpeakersStr(self) -> str:
        ret = "【" + self.name + "】\n"
        
        for speaker_name in self.speakers:
            ret += self.speakers[speaker_name].getStylesStr() + "\n"
        
        return ret
    
    def hasSpeaker(self, name) -> bool:
        if name in self.speakers.keys():
            return True
        else:
            return False
    
    def getSpeaker(self, name) -> VoiceVoxVoiceSpeaker:
        return self.speakers[name]
    
    def hasStyle(self, speaker_name, style_name) -> bool:
        if self.hasSpeaker(speaker_name):
            speaker = self.speakers[speaker_name]
            if speaker.hasStyle(style_name):
                return True
        
        return False
    
    def getName(self) -> str:
        return self.name
    
    def getSpeakerWithStyleId(self, id:int) -> VoiceVoxVoiceSpeaker:
        for speaker in self.speakers.values():
            if speaker.hasStyleId(id):
                return speaker
        return None
    
    def getSpeakersDict(self) -> dict:
        return self.speakers