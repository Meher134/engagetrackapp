# AI-Powered Interactive Learning Assistant for Classrooms (Problem Statement 4)
## Intel Unnati Industrial training May - July 2025
## Team Members (GITAM)
1. Meher Sai Sanjana Potukuchi (Trainee)
2. Polamarasetti Gowtam (Trainee)
3. Suraj Aravind B (Facualty Mentor)



## Project Overview

An AI-integrated classroom engagement system that evaluates student understanding by analyzing typed essays based on voice-recorded lectures. The system captures typing behavior, uses NLP similarity and stylometric analysis to score engagement, and allows lecturers to view detailed analytics per class and student.


## Steps to run this project

### 1. Open a Desired Folder in a Code Editor

Use any code editor like VS Code or PyCharm.

### 2. Clone the Repository

```bash
git clone https://github.com/Meher134/engagetrackapp.git
cd engagetrackapp
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

### 4. Activate the Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Set Up MongoDB Atlas

- Create a free cluster at [MongoDB Atlas](https://www.mongodb.com/products/platform/atlas-database)
- Create a user with username and password (avoid special characters)
- Whitelist your IP
- Copy your connection string

### 7. Create `.env` File

In the project root directory, create a `.env` file and add:

```env
MONGO_URL="your-mongodb-connection-string"
SESSION_SECRET_KEY="your-super-secure-random-key"
```

**Example:**
```env
MONGO_URL="mongodb+srv://GOPO:gvnvjfvn@studcluster.kjxqjho.mongodb.net/?retryWrites=true&w=majority&appName=STUDCluster"
SESSION_SECRET_KEY="A1B2C3D4E5F6G7H8"
```

### 8. Run the Application

```bash
uvicorn main:app --reload
```

### 9. Open in Browser

Go to:

```
http://127.0.0.1:8000
```

---


