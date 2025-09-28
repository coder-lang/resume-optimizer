import os
import re
import io
import base64
import json
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string
from markupsafe import Markup
from openai import OpenAI
import secrets
import qrcode

app = Flask(__name__)

TOKEN_FILE = "/tmp/resume_tokens.json"

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)

def is_access_valid():
    token = request.args.get('token')
    if not token:
        return False
    tokens = load_tokens()
    if token in tokens:
        expiry = tokens[token]
        if datetime.utcnow().isoformat() < expiry:
            return True
    return False

def get_ai_response(prompt, model="gpt-4o-mini"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

def calculate_real_ats_score(job_desc, resume_text):
    # Extract words (min 3 letters, ignore common stop words)
    job_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', job_desc.lower()))
    resume_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', resume_text.lower()))
    matched = len(job_words & resume_words)
    total = len(job_words)
    return min(100, int((matched / total) * 100)) if total > 0 else 0

# ===== HTML TEMPLATE (unchanged) =====
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

    input, textarea {
      width: 100%;
      padding: 16px;
      border: 2px solid var(--border);
      border-radius: 12px;
      font-size: 16px;
      font-family: inherit;
      transition: all 0.3s ease;
      background: #fafbff;
    }

    textarea {
      resize: vertical;
      min-height: 100px;
    }

    input:focus, textarea:focus {
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

    .exp-section {
      background: #f8fafc;
      padding: 20px;
      border-radius: 12px;
      margin-bottom: 20px;
      border: 1px dashed #cbd5e1;
    }

    footer {
      text-align: center;
      padding: 20px;
      color: var(--gray);
      font-size: 0.9rem;
    }

    @media (max-width: 600px) {
      h1 { font-size: 2rem; }
      .card-body { padding: 24px 20px; }
      .btn { padding: 14px; font-size: 16px; }
      .score-badge { font-size: 1.5rem; padding: 10px 16px; }
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
      <p class="subtitle">AI-powered resume that beats ATS and lands interviews — in 10 seconds.</p>
    </header>

    <div class="card">
      <div class="card-header">
        <h2 class="card-title"><i class="fas fa-edit"></i> Build Your AI-Optimized Resume</h2>
      </div>
      <div class="card-body">
        <form method="POST">
          <div class="form-group">
            <label><i class="fas fa-user"></i> Full Name</label>
            <input type="text" name="name" value="{{ name or '' }}" required>
          </div>

          <div class="form-group">
            <label><i class="fas fa-envelope"></i> Email</label>
            <input type="email" name="email" value="{{ email or '' }}" required>
          </div>

          <div class="form-group">
            <label><i class="fas fa-phone"></i> Phone (Optional)</label>
            <input type="text" name="phone" value="{{ phone or '' }}">
          </div>

          <div class="form-group">
            <label><i class="fas fa-briefcase"></i> Target Job Title</label>
            <input type="text" name="job_title" value="{{ job_title or '' }}" placeholder="e.g., Senior Product Manager" required>
          </div>

          <div class="form-group">
            <label><i class="fas fa-file-alt"></i> Job Description</label>
            <textarea name="job_desc" placeholder="Paste the full job description here..." required>{{ job_desc or '' }}</textarea>
          </div>

          <div class="form-group">
            <label><i class="fas fa-building"></i> Work Experience</label>
            <p style="margin-bottom: 12px; color: var(--gray);">Add your current/most recent role. Optionally add a second.</p>

            <!-- Role 1 (Required) -->
            <div class="exp-section">
              <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px;">
                  <input type="text" name="company_0" placeholder="Company *" value="{{ experiences[0].company if experiences and experiences|length > 0 else '' }}" required>
                </div>
                <div style="flex: 1; min-width: 200px;">
                  <input type="text" name="role_0" placeholder="Your Title *" value="{{ experiences[0].role if experiences and experiences|length > 0 else '' }}" required>
                </div>
                <div style="flex: 1; min-width: 200px;">
                  <input type="text" name="duration_0" placeholder="Duration" value="{{ experiences[0].duration if experiences and experiences|length > 0 else '' }}">
                </div>
              </div>
              <textarea name="bullets_0" placeholder="• Led a team of 5...&#10;• Increased revenue by 30...">{{ 
                (experiences[0].bullets|join('\n') if experiences and experiences|length > 0 else '') 
              }}</textarea>
            </div>

            <!-- Role 2 (Optional) -->
            <div class="exp-section">
              <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px;">
                  <input type="text" name="company_1" placeholder="Company (optional)" value="{{ experiences[1].company if experiences and experiences|length > 1 else '' }}">
                </div>
                <div style="flex: 1; min-width: 200px;">
                  <input type="text" name="role_1" placeholder="Your Title (optional)" value="{{ experiences[1].role if experiences and experiences|length > 1 else '' }}">
                </div>
                <div style="flex: 1; min-width: 200px;">
                  <input type="text" name="duration_1" placeholder="Duration" value="{{ experiences[1].duration if experiences and experiences|length > 1 else '' }}">
                </div>
              </div>
              <textarea name="bullets_1" placeholder="• Managed cross-functional projects...">{{ 
                (experiences[1].bullets|join('\n') if experiences and experiences|length > 1 else '') 
              }}</textarea>
            </div>
          </div>

          <button class="btn" type="submit">
            <i class="fas fa-bolt"></i> Generate AI-Optimized Resume
          </button>
        </form>

        {% if error %}
        <div class="error">
          {{ error }}
        </div>
        {% endif %}

        {% if result_text %}
        <div class="result-card">
          <div class="ats-meter">
            <div class="score-badge">{{ score }}%</div>
            <div>
              <div class="score-label">ATS Optimization Score</div>
              <div class="keywords">Optimized for "{{ job_title }}"</div>
            </div>
          </div>

          <div class="output" id="output">{{ result_text }}</div>

          <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('output').innerText).then(() => {this.innerHTML='<i class=\'fas fa-check\'></i> Copied!'; setTimeout(() => this.innerHTML='<i class=\'fas fa-copy\'></i> Copy Full Resume', 2000);})">
            <i class="fas fa-copy"></i> Copy Full Resume
          </button>
        </div>
        {% endif %}
      </div>
    </div>

    <footer>
      <p>© 2025 ResumeTailor · AI that gets you interviews</p>
    </footer>
  </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/admin/token')
def admin_token():
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key:
        return "ADMIN_KEY not set in environment", 500
    if request.args.get('key') != admin_key:
        return "Access denied", 403
    token = secrets.token_urlsafe(16)
    expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    tokens = load_tokens()
    tokens[token] = expiry
    save_tokens(tokens)
    link = f"https://resume-optimizer-briq.onrender.com/?token={token}"
    return f'''
    <div style="font-family: sans-serif; padding: 30px; max-width: 600px; margin: 0 auto;">
        <h2>✅ Token Generated for Paying User</h2>
        <p>Send this link to the user on WhatsApp:</p>
        <input type="text" value="{link}" style="width:100%; padding:12px; font-size:16px;" onclick="this.select()" readonly />
        <p style="margin-top: 20px;"><a href="{link}" target="_blank">🔗 Test Link</a></p>
        <p style="color: #666; font-size: 14px;">Token expires in 24 hours.</p>
    </div>
    '''

@app.route('/', methods=['POST'])
def optimize():
    if not is_access_valid():
        # === PAYMENT WALL (UNCHANGED) ===
        upi_id = "goodluckankur@okaxis"
        amount = "49.00"
        name = "ResumeTailor"
        note = "24-hour access"
        upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={note}&cu=INR"

        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(upi_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        qr_data_uri = f"data:image/png;base64,{img_base64}"

        error = Markup(f'''
        <div style="text-align: center; max-width: 600px; margin: 0 auto;">
          <div style="font-size: 24px; font-weight: 700; color: #1e40af; margin-bottom: 16px;">🔒 Secure Access Required</div>
          <p style="color: #4b5563; line-height: 1.6; margin-bottom: 20px;">
            To prevent abuse and ensure quality, we offer <strong>24-hour unlimited access</strong> for a small fee of <strong>₹49</strong> (less than a coffee).
          </p>

          <div style="background: white; padding: 20px; border-radius: 12px; margin: 20px 0; text-align: center; border: 1px solid #e2e8f0;">
            <h3 style="margin-bottom: 12px; color: #1d4ed8;">📱 Scan to Pay ₹49 via UPI</h3>
            <img src="{qr_data_uri}" alt="UPI QR Code" style="max-width: 220px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);" />
            <p style="font-size: 14px; color: #374151; margin-top: 12px;">
              <strong>UPI ID:</strong> goodluckankur@okaxis
            </p>
            <p style="font-size: 13px; color: #6b7280; margin-top: 6px;">
              Works with Google Pay, PhonePe, Paytm, BHIM, and all UPI apps.
            </p>
          </div>

          <div style="background: white; padding: 16px; border-radius: 12px; margin: 20px 0; text-align: left; border: 1px solid #e2e8f0;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
              <span style="background: #dbeafe; color: #1d4ed8; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;">1</span>
              <strong>Pay via UPI</strong>
            </div>
            <p style="margin-left: 40px; color: #374151;">Scan the QR code above (₹49 auto-filled).</p>
            
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
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        job_title = request.form.get('job_title', '')
        job_desc = request.form.get('job_desc', '')
        experiences = []
        for i in range(2):
            company = request.form.get(f'company_{i}', '')
            role = request.form.get(f'role_{i}', '')
            if company or role:
                duration = request.form.get(f'duration_{i}', '')
                bullets_raw = request.form.get(f'bullets_{i}', '')
                bullets = [line.strip() for line in bullets_raw.split('\n') if line.strip()]
                experiences.append({"company": company, "role": role, "duration": duration, "bullets": bullets})
        return render_template_string(HTML,
            name=name,
            email=email,
            phone=phone,
            job_title=job_title,
            job_desc=job_desc,
            experiences=experiences,
            error=error
        )

    # === FULL RESUME PROCESSING (IMPROVED LOGIC) ===
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        job_title = request.form.get('job_title', '').strip()
        job_desc = request.form.get('job_desc', '').strip()

        experiences = []
        for i in range(2):
            company = request.form.get(f'company_{i}', '').strip()
            role = request.form.get(f'role_{i}', '').strip()
            if not company or not role:
                if i == 0:
                    raise ValueError("Please fill in your first work experience.")
                else:
                    continue
            duration = request.form.get(f'duration_{i}', '').strip()
            bullets_raw = request.form.get(f'bullets_{i}', '')
            bullets = []
            for line in bullets_raw.split('\n'):
                clean = line.strip()
                if clean:
                    if clean.startswith(('•', '-', '*')):
                        clean = clean[1:].strip()
                    bullets.append(clean)
            experiences.append({"company": company, "role": role, "duration": duration, "bullets": bullets})

        # Professional Summary
        summary = get_ai_response(f"""
        Write a 3-sentence professional summary for a {job_title}.
        Use keywords from this job description: {job_desc}.
        Focus on measurable impact, relevant skills, and seniority. Avoid pronouns.
        Start with the job title. No fluff.
        """)

        # Enhanced Bullets (with smarter prompt)
        enhanced_experiences = []
        for exp in experiences:
            enhanced_bullets = []
            for bullet in exp["bullets"]:
                if not bullet:
                    continue
                improved = get_ai_response(f"""
                You are an expert resume writer for {job_title} roles.
                Original bullet: "{bullet}"
                Job description: {job_desc}
                Instructions:
                - If the original implies scale, result, or impact, enhance it with a realistic metric.
                - If it's descriptive, focus on technical specificity (tools, architecture, outcome) — DO NOT invent fake percentages.
                - Use strong past-tense verbs: Engineered, Led, Designed, Deployed, Optimized.
                - Include 1–2 keywords from the job description.
                - Keep under 25 words.
                - NEVER say "by 30%" unless the original implies it.
                Return ONLY the improved bullet.
                """).strip().strip('"').strip("'")
                enhanced_bullets.append(improved)
            enhanced_experiences.append({**exp, "bullets": enhanced_bullets})

        # REAL ATS SCORE (keyword-based)
        all_content = summary + " " + " ".join(b for exp in enhanced_experiences for b in exp["bullets"])
        score = calculate_real_ats_score(job_desc, all_content)

        # Format output
        lines = [name]
        contact = []
        if email: contact.append(email)
        if phone: contact.append(phone)
        if contact: lines.append(" | ".join(contact))
        lines += ["", "PROFESSIONAL SUMMARY", summary, "", "WORK EXPERIENCE"]
        for exp in enhanced_experiences:
            lines.append(f"{exp['role']} | {exp['company']}")
            if exp['duration']: lines.append(exp['duration'])
            for b in exp['bullets']:
                lines.append(f"• {b}")
            lines.append("")
        lines.append(f"[AI Resume Score: {score}/100 — ATS Optimized]")
        result_text = "\n".join(lines)

        return render_template_string(HTML,
            name=name,
            email=email,
            phone=phone,
            job_title=job_title,
            job_desc=job_desc,
            experiences=experiences,
            result_text=result_text,
            score=score
        )

    except Exception as e:
        error = Markup(f'<div style="color:#ef4444;padding:15px;background:#fef2f2;border-radius:8px;">⚠️ {str(e)}</div>')
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        job_title = request.form.get('job_title', '')
        job_desc = request.form.get('job_desc', '')
        experiences = []
        for i in range(2):
            company = request.form.get(f'company_{i}', '')
            role = request.form.get(f'role_{i}', '')
            if company or role:
                duration = request.form.get(f'duration_{i}', '')
                bullets_raw = request.form.get(f'bullets_{i}', '')
                bullets = [line.strip() for line in bullets_raw.split('\n') if line.strip()]
                experiences.append({"company": company, "role": role, "duration": duration, "bullets": bullets})
        return render_template_string(HTML,
            name=name,
            email=email,
            phone=phone,
            job_title=job_title,
            job_desc=job_desc,
            experiences=experiences,
            error=error
        )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
