# Internship Recommendation System 🚀

## 📌 Overview
An intelligent web application that recommends internships based on user skills and resume analysis using Machine Learning and NLP techniques.

The system analyzes user input and uploaded resumes to provide personalized internship suggestions along with skill gap insights and match scores.

---

## 🎯 Key Features

- 🔍 Skill-based Internship Recommendation  
- 📄 Resume Upload & NLP-based Analysis  
- 🤖 BERT-based Skill Extraction  
- 📊 Match Score Calculation using Cosine Similarity  
- 📈 Skill Gap Identification & Future Suggestions  
- 🌐 Multi-language Support (Regional Indian Languages)  
- 💾 Save & Track Internship Applications  

---

## 🧠 How It Works

1. User enters skills or uploads resume  
2. Resume is processed using NLP techniques  
3. Skills are extracted using BERT model  
4. Internship dataset is compared using Cosine Similarity  
5. System outputs:
   - Recommended internships  
   - Match score  
   - Missing skills (skill gap)  
   - Future learning suggestions  

---

## 🛠️ Tech Stack

- **Backend:** Django, Python  
- **Frontend:** HTML, CSS  
- **Machine Learning:**  
  - NLP  
  - BERT  
  - Cosine Similarity  
- **Other Tools:** Resume Parser  

---

## ⚙️ Installation & Setup

```bash
git clone https://github.com/sashankrudra-creator/internship-recommendation-system.git
cd internship-recommendation-system
pip install -r requirements.txt
python manage.py runserver
