import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-5", temperature=0, api_key=openai_api_key)


prompt = ChatPromptTemplate.from_template(
    "Please modify the following text to be more concise and informative: {text}"
)

class SummarizedText(BaseModel):
    summarized_text: str = Field(..., description="The summarized text")
    original_text: str = Field(..., description="The original text provided")
    size : int = Field(..., description="The size of the summarized text")
    
class CopyEditedText(BaseModel):
    copy_edited_text: str = Field(..., description="The copy edited text")
    original_text: str = Field(..., description="The original text provided")
    is_modified: bool = Field(..., description="Whether the text was modified")
    

class TextModifiers:
    
    def __init__(self):
       openai_api_key = os.getenv("OPENAI_API_KEY")
       self.llm = ChatOpenAI(model="gpt-5", temperature=0, api_key=openai_api_key)
       self.summarizer = self.llm.with_structured_output(SummarizedText)
       self.copy_editor = self.llm.with_structured_output(CopyEditedText)
       self._load_summarizer_prompt()
       self._load_copy_editor_prompt()
       
    def summarize(self, text: str) -> SummarizedText:
        return self.summarizer.invoke(text)
   
    def copy_edit(self, text:str) -> CopyEditedText:
       return self.copy_editor.invoke(text)
       
       
       
    def _load_summarizer_prompt(self):
        with open("prompts/summarizer.md", "r") as f:
            self.summarizer_prompt = f.read()
            
     
    
    def _load_copy_editor_prompt(self):
        with open("prompts/copy_editor.md", "r") as f:
            self.copy_editor_prompt = f.read()
    
    
            
            
            
    

        