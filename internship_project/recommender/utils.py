import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter


# ===============================
# 🔹 INTERNSHIP RECOMMENDATION
# ===============================
def intern(student_profile, internships_df):
    """
    Returns sorted internship recommendations with match score.
    student_profile: {"Skills_ILE": "python, ml"}
    internships_df: dataframe of internships
    """

    # Safety check
    if internships_df is None or internships_df.empty:
        return pd.DataFrame({"Error": ["No internship data available"]})

    df = internships_df.copy()

    # 🔹 Create combined text column
    df["Skills_Required_ILE"] = (
        df["Skills_Required"].fillna("").astype(str) + " " +
        df["Interest_Area"].fillna("").astype(str) + " " +
        df["Location"].fillna("").astype(str) + " " +
        df["Education _Level"].fillna("").astype(str)
    )

    # 🔹 TF-IDF
    vectorizer = TfidfVectorizer(stop_words="english")
    internship_matrix = vectorizer.fit_transform(df["Skills_Required_ILE"])

    # IMPORTANT FIX: must be list
    student_text = [student_profile.get("Skills_ILE", "")]
    student_vector = vectorizer.transform(student_text)

    # 🔹 Cosine similarity
    similarities = cosine_similarity(student_vector, internship_matrix).flatten()

    df["Match_Score"] = similarities
    df["Match_Percentage"] = (similarities * 100).round(2)

    # 🔹 Filter results > 2%
    df = df[df["Match_Percentage"] > 2]

    # 🔹 Return top matches
    return df.sort_values(by="Match_Score", ascending=False).head(10)


# ===============================
# 🔹 SKILL GAP ANALYSIS
# ===============================
def analyze_skill_gaps(user_skills, recommendations):
    """
    user_skills: list like ["python", "sql"]
    recommendations: list of dicts (top internships)
    """

    if not recommendations:
        return []

    # 🔹 collect required skills
    all_required_skills = []

    for rec in recommendations:
        skills_text = rec.get("Skills_Required", "")
        if skills_text:
            skills = str(skills_text).split(",")
            all_required_skills.extend(
                [s.strip().lower() for s in skills if s.strip()]
            )

    # 🔹 normalize user skills
    user_skills_normalized = [
        s.lower().strip() for s in user_skills if s.strip()
    ]

    # 🔹 find missing skills
    missing_skills = []

    for skill in all_required_skills:
        found = False

        for user_skill in user_skills_normalized:
            if skill in user_skill or user_skill in skill:
                found = True
                break

        if not found and skill not in missing_skills:
            missing_skills.append(skill)

    # 🔹 frequency count
    skill_counts = Counter(all_required_skills)

    missing_with_freq = [
        (skill, skill_counts[skill]) for skill in missing_skills
    ]

    missing_with_freq.sort(key=lambda x: x[1], reverse=True)

    # 🔹 return top gaps
    top_missing = [
        {"skill": skill, "frequency": freq}
        for skill, freq in missing_with_freq[:10]
    ]

    return top_missing