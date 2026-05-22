FROM python:3.12-slim
COPY . /ai-agent        
WORKDIR /ai-agent
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-m", "src.agent"] 

