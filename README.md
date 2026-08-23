# Sakro

Sakro is a small website that shows network packets from a file named `traffic.csv`. It marks packets that look unusual. It is a learning project, not a full security product.

## Put it on Render

Render looks for a Python file named **app.py**. That file must be in this GitHub repo (the same one Render is connected to).

In Render, use these settings:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`

After GitHub has the new files, open your Render service and click **Manual Deploy**.

Free Render websites go to sleep when nobody visits. The first load after that can take about a minute.

You do not need to put Backblaze keys in GitHub. If you use Backblaze later, add the keys in Render as environment variables, or keep them in a local `.env` file on your computer.

## Run it on your computer

```
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

Packet capture (`packet_capture.py`) only works on your own computer. It will not capture your home network from Render.
