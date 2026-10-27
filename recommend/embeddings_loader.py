import zipfile
import pandas as pd
from sentence_transformers import SentenceTransformer


model = SentenceTransformer('all-MiniLM-L6-v2')

# Loads the zip file into a readable csv 
with zipfile.ZipFile('hobbies.zip') as z:
    with z.open('hobbies.csv') as f:
        hobbies_df = pd.read_csv(f, on_bad_lines='skip')

# Drops all duplicate hobbies and sets them all lowercase
hobbies_df = hobbies_df.drop_duplicates(subset='HOBBIES').reset_index(drop=True)
hobbies_df['HOBBIES'] = hobbies_df['HOBBIES'].astype(str).str.lower()

# Loads education and religion csvs
education_df = pd.read_csv("education.csv")
religion_df = pd.read_csv("religion.csv")

# Used for embedding columns 
def embed_column(df, column):
    return {
        row[column]: model.encode(row[column]).tolist()
        for _, row in df.iterrows()
    }

# Create embedding dictionaries
relig_emb = embed_column(religion_df, "religion")
edu_emb = embed_column(education_df, "education")
