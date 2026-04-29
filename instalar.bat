@echo off
echo ==========================================
echo Preparando o Robo do Oitchau...
echo ==========================================
echo.
echo 1. Criando ambiente virtual...
python -m venv venv

echo 2. Ativando e instalando bibliotecas...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo 3. Baixando o navegador invisivel (Chromium)...
playwright install chromium

echo.
echo ==========================================
echo TUDO PRONTO! INSTALACAO CONCLUIDA!
echo Voce so precisa fazer isso uma vez na vida.
echo Pode fechar esta tela e usar o "rodar.bat"
echo ==========================================
pause