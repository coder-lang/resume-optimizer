import os
import re
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string
from markupsafe import Markup
from openai import OpenAI
import secrets

app = Flask(__name__)

# In-memory token store (resets on deploy — fine for MVP)
valid_tokens = {}

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ResumeTailor · AI-Powered ATS Optimizer</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --success: #10b981;
      --light: #f9fafb;
      --dark: #111827;
      --gray: #6b7280;
      --border: #e5e7eb;
      --shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
      --radius: 16px;
    }

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
      color: var(--dark);
      line-height: 1.6;
      min-height: 100vh;
      padding: 20px;
    }

    .container {
      max-width: 850px;
      margin: 0 auto;
    }

    header {
      text-align: center;
      padding: 40px 20px 30px;
    }

    .logo {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .logo-icon {
      background: linear-gradient(135deg, var(--primary), #8b5cf6);
      width: 48px;
      height: 48px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 20px;
      box-shadow: var(--shadow);
    }

    h1 {
      font-size: 2.5rem;
      font-weight: 800;
      background: linear-gradient(to right, #1e40af, #7c3aed);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      margin-bottom: 12px;
    }

    .subtitle {
      font-size: 1.1rem;
      color: var(--gray);
      max-width: 600px;
      margin: 0 auto;
    }

    .card {
      background: white;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
      margin-bottom: 30px;
    }

    .card-header {
      padding: 24px 32px;
      background: #f8fafc;
      border-bottom: 1px solid var(--border);
    }

    .card-title {
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--dark);
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .card-body {
      padding: 32px;
    }

    .form-group {
      margin-bottom: 24px;
    }

    label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      margin-bottom: 10px;
      color: var(--dark);
    }

    textarea {
      width: 100%;
      padding: 16px;
      border: 2px solid var(--border);
      border-radius: 12px;
      font-size: 16px;
      font-family: inherit;
      resize: vertical;
      min-height: 120px;
      transition: all 0.3s ease;
      background: #fafbff;
    }

    textarea:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2);
    }

    .btn {
      background: linear-gradient(135deg, var(--primary-dark), #7c3aed);
      color: white;
      border: none;
      padding: 16px 32px;
      font-size: 18px;
      font-weight: 700;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
    }

    .btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }

    .error {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 25px;
      margin: 25px 0;
    }

    .result-card {
      background: linear-gradient(135deg, #f0fdf4, #dcfce7);
      border: 2px solid #bbf7d0;
      border-radius: var(--radius);
      padding: 28px;
      margin-top: 20px;
      animation: fadeIn 0.5s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .ats-meter {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }

    .score-badge {
      background: white;
      color: var(--success);
      font-weight: 800;
      font-size: 1.8rem;
      padding: 12px 24px;
      border-radius: 16px;
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
      min-width: 120px;
      text-align: center;
    }

    .score-label {
      font-size: 1.1rem;
      font-weight: 600;
      color: #065f46;
    }

    .keywords {
      font-size: 0.95rem;
      color: var(--gray);
      background: rgba(16, 185, 129, 0.1);
      padding: 6px 12px;
      border-radius: 20px;
      display: inline-block;
    }

    .output {
      background: white;
      padding: 24px;
      border-radius: 14px;
      font-family: 'SFMono-Regular', 'Consolas', monospace;
      white-space: pre-wrap;
      margin: 24px 0;
      border: 1px solid #d1fae5;
      font-size: 16px;
      line-height: 1.7;
      color: #065f46;
    }

    .copy-btn {
      background: white;
      color: var(--primary-dark);
      border: 2px solid var(--primary);
      padding: 14px 28px;
      font-weight: 700;
      border-radius: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      transition: all 0.2s ease;
      width: 100%;
      font-size: 16px;
    }

    .copy-btn:hover {
      background: #f0f9ff;
      transform: scale(1.02);
    }

    footer {
      text-align: center;
      padding: 20px;
      color: var(--gray);
      font-size: 0.9rem;
    }

    @media (max-width: 600px) {
      h1 {
        font-size: 2rem;
      }
      .card-body {
        padding: 24px 20px;
      }
      .btn {
        padding: 14px;
        font-size: 16px;
      }
      .score-badge {
        font-size: 1.5rem;
        padding: 10px 16px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo">
        <div class="logo-icon">
          <i class="fas fa-robot"></i>
        </div>
      </div>
      <h1>ResumeTailor</h1>
      <p class="subtitle">AI-powered resume bullets that beat ATS and land interviews — in 10 seconds.</p>
    </header>

    <div class="card">
      <div class="card-header">
        <h2 class="card-title"><i class="fas fa-edit"></i> Optimize Your Resume</h2>
      </div>
      <div class="card-body">
        <form method="POST">
          <div class="form-group">
            <label><i class="fas fa-file-alt"></i> Your Resume Bullets</label>
            <textarea name="resume" placeholder="- Managed a team of 5 developers&#10;- Reduced server costs by 30% using AWS optimization">{{ resume or '' }}</textarea>
          </div>

          <div class="form-group">
            <label><i class="fas fa-briefcase"></i> Job Description</label>
            <textarea name="job_desc" placeholder="We're seeking a Senior DevOps Engineer with expertise in AWS, Kubernetes, and CI/CD pipelines...">{{ job_desc or '' }}</textarea>
          </div>

          <button class="btn" type="submit">
            <i class="fas fa-bolt"></i> Optimize for ATS
          </button>
        </form>

        {% if error %}
        <div class="error">
          {{ error }}
        </div>
        {% endif %}

        {% if result %}
        <div class="result-card">
          <div class="ats-meter">
            <div class="score-badge">{{ score }}%</div>
            <div>
              <div class="score-label">ATS Optimization Score</div>
              <div class="keywords">{{ matched }}/{{ total }} keywords matched</div>
            </div>
          </div>

          <div class="output" id="output">{{ result }}</div>

          <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('output').innerText).then(() => {this.innerHTML='<i class=\'fas fa-check\'></i> Copied!'; setTimeout(() => this.innerHTML='<i class=\'fas fa-copy\'></i> Copy Optimized Bullets', 2000);})">
            <i class="fas fa-copy"></i> Copy Optimized Bullets
          </button>
        </div>
        {% endif %}
      </div>
    </div>

    <footer>
      <p>© 2024 ResumeTailor · AI that gets you interviews</p>
    </footer>
  </div>
</body>
</html>
'''

def is_access_valid():
    token = request.args.get('token')
    if token and token in valid_tokens:
        expiry = valid_tokens[token]
        if datetime.utcnow().isoformat() < expiry:
            return True
    return False

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/success')
def payment_success():
    # Kept for future use — not used in WhatsApp flow
    token = secrets.token_urlsafe(16)
    expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    valid_tokens[token] = expiry
    return f'<script>alert("Thank you! You now have 24-hour access."); window.location.replace("https://resume-optimizer-briq.onrender.com/?token={token}");</script>'

@app.route('/', methods=['POST'])
def optimize():
    if not is_access_valid():
        error = Markup('''
        <div style="text-align: center; max-width: 600px; margin: 0 auto;">
          <div style="font-size: 24px; font-weight: 700; color: #1e40af; margin-bottom: 16px;">🔒 Secure Access Required</div>
          <p style="color: #4b5563; line-height: 1.6; margin-bottom: 20px;">
            To prevent abuse and ensure quality, we offer <strong>24-hour unlimited access</strong> for a small fee of <strong>₹49</strong> (less than a coffee).
          </p>
          <div style="background: white; padding: 16px; border-radius: 12px; margin: 20px 0; text-align: left; border: 1px solid #e2e8f0;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
              <span style="background: #dbeafe; color: #1d4ed8; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;">1</span>
              <strong>Pay via UPI</strong>
            </div>
            <p style="margin-left: 40px; color: #374151;">Scan or tap to pay: <strong>goodluckankur@okaxis</strong></p>
            
            <div style="display: flex; align-items: center; gap: 12px; margin: 16px 0;">
              <span style="background: #dcfce7; color: #166534; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;">2</span>
              <strong>WhatsApp your payment screenshot</strong>
            </div>
            <p style="margin-left: 40px; color: #374151;">Send to: <strong>+91 8851233153</strong></p>
            
            <div style="display: flex; align-items: center; gap: 12px; margin-top: 16px;">
              <span style="background: #ffedd5; color: #c2410c; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;">3</span>
              <strong>Get instant access link</strong>
            </div>
            <p style="margin-left: 40px; color: #374151;">Use the AI optimizer as many times as you want for 24 hours.</p>
          </div>
          <p style="font-size: 14px; color: #6b7280; margin-top: 20px;">
            🔐 Payments go directly to the developer. No third parties. No subscriptions.
          </p>
        </div>
        ''')
        return render_template_string(HTML, error=error)
    
    resume = request.form['resume']
    job_desc = request.form['job_desc']
    
    # ATS Score
    def extract_keywords(text):
        words = re.split(r'[,\.\s]+', text.lower())
        return {word.strip() for word in words if len(word.strip()) >= 2}
    
    job_keywords = extract_keywords(job_desc)
    resume_keywords = extract_keywords(resume)
    matched = sum(1 for word in job_keywords if word in resume_keywords)
    total = len(job_keywords)
    score = 0 if total == 0 else min(100, int((matched / total) * 100))
    
    # OpenAI Call
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"""Rewrite this resume bullet to match the job description. 
- Use EXACT keywords from the job description.
- Keep under 25 words.
- No pronouns ("I", "my"), no fluff.

Resume: {resume}
Job: {job_desc}"""}],
            max_tokens=100,
            temperature=0.7
        )
        result = response.choices[0].message.content.strip()
    except Exception as e:
        result = f"Error: {str(e)}"
        return render_template_string(HTML, resume=resume, job_desc=job_desc, error=result)
    
    return render_template_string(HTML, 
                                resume=resume, 
                                job_desc=job_desc, 
                                result=result,
                                score=score,
                                matched=matched,
                                total=total)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)