"""
seed_demo_candidates — create realistic open-to-work demo candidates.

Usage:
    python manage.py seed_demo_candidates           # skip if already seeded
    python manage.py seed_demo_candidates --reset   # delete & recreate
"""
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from ann.models import CandidateProfile, ParsedResume, CandidateSkill

# ---------------------------------------------------------------------------
# Candidate data
# skill tuples: (display_text, category, proficiency 1-5)
# ---------------------------------------------------------------------------
DEMO_CANDIDATES = [
    {
        'username': 'demo_priya_sharma',
        'first_name': 'Priya',
        'last_name': 'Sharma',
        'email': 'priya.sharma@demo.skillsevak',
        'profile': {
            'full_name': 'Priya Sharma',
            'phone': '+91 98765 43210',
            'location': 'Bangalore, Karnataka',
            'experience_years': 6,
            'education_level': 'master',
            'education_field': 'Data Science',
            'salary_expectation': 1800000,
            'open_to_work': True,
        },
        'summary': (
            'Senior Data Scientist with 6 years experience building ML pipelines, '
            'NLP models, and recommendation systems at Infosys and Wipro. '
            'Passionate about turning messy data into business value.'
        ),
        'resume_text': (
            'Priya Sharma — Senior Data Scientist, Bangalore\n\n'
            'SUMMARY\nExperienced Data Scientist specializing in machine learning, '
            'deep learning, and natural language processing. Built production ML systems '
            'serving millions of users. Strong Python and TensorFlow background.\n\n'
            'EXPERIENCE\n'
            'Senior Data Scientist, Infosys (2021–Present)\n'
            '  • Built NLP text classification pipeline achieving 94% accuracy on 10M documents\n'
            '  • Designed recommendation engine boosting CTR by 28%\n'
            '  • Led cross-functional team of 4 data scientists and 2 MLOps engineers\n'
            '  • Deployed models on AWS SageMaker with monitoring dashboards\n\n'
            'Data Scientist, Wipro (2019–2021)\n'
            '  • Developed fraud detection ML model reducing false positives by 40%\n'
            '  • Feature engineering on structured and unstructured data\n'
            '  • A/B testing frameworks for model evaluation\n\n'
            'Data Analyst, TCS (2018–2019)\n'
            '  • SQL queries, Python scripts, Tableau dashboards\n\n'
            'SKILLS\nPython, TensorFlow, PyTorch, Scikit-learn, Keras, '
            'Machine Learning, Deep Learning, NLP, Computer Vision, '
            'SQL, AWS, SageMaker, Docker, Pandas, NumPy, Spark, '
            'Data Analysis, Statistics, A/B Testing, Feature Engineering\n\n'
            'EDUCATION\nM.Tech Data Science — IIT Bangalore (2018)\n'
            'B.Tech Computer Science — NIT Warangal (2016)\n'
        ),
        'skills': [
            ('Python', 'technical', 5),
            ('TensorFlow', 'technical', 5),
            ('PyTorch', 'technical', 4),
            ('Machine Learning', 'technical', 5),
            ('Deep Learning', 'technical', 4),
            ('NLP', 'technical', 4),
            ('Scikit-learn', 'technical', 5),
            ('SQL', 'technical', 4),
            ('AWS', 'technical', 3),
            ('Docker', 'technical', 3),
            ('Pandas', 'technical', 5),
            ('NumPy', 'technical', 4),
            ('Data Analysis', 'domain', 5),
            ('Statistics', 'domain', 4),
            ('Feature Engineering', 'domain', 4),
            ('Team Leadership', 'soft', 3),
        ],
    },
    {
        'username': 'demo_arjun_mehta',
        'first_name': 'Arjun',
        'last_name': 'Mehta',
        'email': 'arjun.mehta@demo.skillsevak',
        'profile': {
            'full_name': 'Arjun Mehta',
            'phone': '+91 91234 56789',
            'location': 'Mumbai, Maharashtra',
            'experience_years': 4,
            'education_level': 'bachelor',
            'education_field': 'Computer Engineering',
            'salary_expectation': 1400000,
            'open_to_work': True,
        },
        'summary': (
            'Full Stack Developer with 4 years building scalable web apps using React, '
            'Node.js, and PostgreSQL. Shipped 12+ production features at two fast-growing startups.'
        ),
        'resume_text': (
            'Arjun Mehta — Full Stack Developer, Mumbai\n\n'
            'SUMMARY\nPassionate full-stack engineer with 4 years delivering end-to-end web '
            'applications. Expert in React frontend and Node.js/Express backend with REST APIs.\n\n'
            'EXPERIENCE\n'
            'Full Stack Developer, Razorpay (2022–Present)\n'
            '  • Built payment dashboard in React with TypeScript, reducing load time by 45%\n'
            '  • Designed REST APIs in Node.js serving 500K daily requests\n'
            '  • PostgreSQL schema design and query optimization\n'
            '  • CI/CD pipelines with GitHub Actions and Docker\n\n'
            'Software Developer, Freshworks (2020–2022)\n'
            '  • Developed customer support widgets using React and Redux\n'
            '  • Integrated third-party APIs (Stripe, Twilio, SendGrid)\n'
            '  • Wrote unit tests with Jest and Cypress E2E tests\n\n'
            'SKILLS\nReact, TypeScript, JavaScript, Node.js, Express.js, '
            'PostgreSQL, MongoDB, Redis, REST API, GraphQL, '
            'Docker, Git, GitHub Actions, Jest, Cypress, '
            'HTML5, CSS3, Tailwind CSS, Redux, Webpack\n\n'
            'EDUCATION\nB.E. Computer Engineering — Mumbai University (2020)\n'
        ),
        'skills': [
            ('React', 'technical', 5),
            ('TypeScript', 'technical', 4),
            ('JavaScript', 'technical', 5),
            ('Node.js', 'technical', 5),
            ('Express.js', 'technical', 4),
            ('PostgreSQL', 'technical', 4),
            ('MongoDB', 'technical', 3),
            ('Redis', 'technical', 3),
            ('REST API', 'technical', 5),
            ('Docker', 'technical', 3),
            ('GraphQL', 'technical', 3),
            ('Git', 'technical', 5),
            ('Jest', 'technical', 4),
            ('Tailwind CSS', 'technical', 4),
            ('Problem Solving', 'soft', 4),
        ],
    },
    {
        'username': 'demo_neha_gupta',
        'first_name': 'Neha',
        'last_name': 'Gupta',
        'email': 'neha.gupta@demo.skillsevak',
        'profile': {
            'full_name': 'Neha Gupta',
            'phone': '+91 88765 32198',
            'location': 'Pune, Maharashtra',
            'experience_years': 3,
            'education_level': 'bachelor',
            'education_field': 'Information Technology',
            'salary_expectation': 1100000,
            'open_to_work': True,
        },
        'summary': (
            'Frontend Developer specializing in React and TypeScript. '
            'Built pixel-perfect UIs for fintech and e-commerce, reducing bounce rates by 22%.'
        ),
        'resume_text': (
            'Neha Gupta — Frontend Developer, Pune\n\n'
            'SUMMARY\nCreative and performance-focused frontend developer with 3 years '
            'building responsive, accessible web interfaces. Strong eye for UI/UX design.\n\n'
            'EXPERIENCE\n'
            'Frontend Developer, PhonePe (2022–Present)\n'
            '  • Built React component library used across 6 product teams\n'
            '  • Improved Lighthouse performance score from 62 to 94\n'
            '  • Implemented micro-frontends architecture with Module Federation\n'
            '  • Accessibility audits (WCAG 2.1 AA compliance)\n\n'
            'UI Developer, Swiggy (2021–2022)\n'
            '  • Responsive menu and checkout flows in React\n'
            '  • Animations with Framer Motion and CSS transitions\n'
            '  • Integrated Google Maps API and payment gateways\n\n'
            'SKILLS\nReact, TypeScript, JavaScript, Vue.js, Next.js, '
            'HTML5, CSS3, Tailwind CSS, SASS/SCSS, Figma, '
            'Jest, React Testing Library, Storybook, '
            'Webpack, Vite, Git, Framer Motion, Accessibility\n\n'
            'EDUCATION\nB.Sc. Information Technology — Pune University (2021)\n'
        ),
        'skills': [
            ('React', 'technical', 5),
            ('TypeScript', 'technical', 4),
            ('JavaScript', 'technical', 5),
            ('Vue.js', 'technical', 3),
            ('Next.js', 'technical', 4),
            ('CSS3', 'technical', 5),
            ('Tailwind CSS', 'technical', 5),
            ('SASS', 'technical', 4),
            ('Figma', 'technical', 4),
            ('Storybook', 'technical', 3),
            ('Webpack', 'technical', 3),
            ('Accessibility', 'domain', 4),
            ('UI/UX', 'domain', 4),
            ('Attention to Detail', 'soft', 5),
        ],
    },
    {
        'username': 'demo_rahul_verma',
        'first_name': 'Rahul',
        'last_name': 'Verma',
        'email': 'rahul.verma@demo.skillsevak',
        'profile': {
            'full_name': 'Rahul Verma',
            'phone': '+91 99887 65432',
            'location': 'Hyderabad, Telangana',
            'experience_years': 7,
            'education_level': 'bachelor',
            'education_field': 'Computer Science',
            'salary_expectation': 2200000,
            'open_to_work': True,
        },
        'summary': (
            'Senior DevOps/SRE Engineer with 7 years automating cloud infrastructure. '
            'Reduced deployment time by 70% at Ola. Expert in Kubernetes, Terraform, and AWS.'
        ),
        'resume_text': (
            'Rahul Verma — Senior DevOps Engineer, Hyderabad\n\n'
            'SUMMARY\nDevOps and Site Reliability Engineer with 7 years building and operating '
            'large-scale cloud infrastructure. Expert in Kubernetes orchestration, '
            'CI/CD automation, and infrastructure-as-code.\n\n'
            'EXPERIENCE\n'
            'Senior DevOps Engineer, Ola (2020–Present)\n'
            '  • Managed Kubernetes cluster with 1200+ microservices across 3 regions\n'
            '  • Built Terraform modules for AWS infrastructure; cut provisioning time by 70%\n'
            '  • Implemented GitOps with ArgoCD for zero-downtime deployments\n'
            '  • Prometheus + Grafana observability stack; reduced MTTR by 60%\n\n'
            'DevOps Engineer, MakeMyTrip (2018–2020)\n'
            '  • Jenkins and GitHub Actions CI/CD pipelines\n'
            '  • Docker containerization of legacy monolith services\n'
            '  • AWS EKS, RDS, ElastiCache, S3 management\n\n'
            'Systems Engineer, HCL (2017–2018)\n'
            '  • Linux administration, shell scripting, monitoring\n\n'
            'SKILLS\nKubernetes, Docker, Terraform, AWS, GCP, Ansible, '
            'Jenkins, GitHub Actions, ArgoCD, Helm, '
            'Prometheus, Grafana, ELK Stack, Linux, Bash, Python, '
            'CI/CD, GitOps, Infrastructure as Code, SRE\n\n'
            'EDUCATION\nB.Tech Computer Science — JNTU Hyderabad (2017)\n'
        ),
        'skills': [
            ('Kubernetes', 'technical', 5),
            ('Docker', 'technical', 5),
            ('Terraform', 'technical', 5),
            ('AWS', 'technical', 5),
            ('GCP', 'technical', 3),
            ('Ansible', 'technical', 4),
            ('Jenkins', 'technical', 4),
            ('GitHub Actions', 'technical', 4),
            ('ArgoCD', 'technical', 4),
            ('Helm', 'technical', 4),
            ('Prometheus', 'technical', 4),
            ('Grafana', 'technical', 4),
            ('Linux', 'technical', 5),
            ('Bash', 'technical', 5),
            ('Python', 'technical', 3),
            ('CI/CD', 'domain', 5),
            ('Infrastructure as Code', 'domain', 5),
        ],
    },
    {
        'username': 'demo_ananya_reddy',
        'first_name': 'Ananya',
        'last_name': 'Reddy',
        'email': 'ananya.reddy@demo.skillsevak',
        'profile': {
            'full_name': 'Ananya Reddy',
            'phone': '+91 87654 32109',
            'location': 'Chennai, Tamil Nadu',
            'experience_years': 4,
            'education_level': 'master',
            'education_field': 'Artificial Intelligence',
            'salary_expectation': 1600000,
            'open_to_work': True,
        },
        'summary': (
            'ML Engineer with 4 years building NLP and computer vision systems. '
            'Fine-tuned BERT models for document classification and deployed on GCP Vertex AI.'
        ),
        'resume_text': (
            'Ananya Reddy — ML Engineer, Chennai\n\n'
            'SUMMARY\nMachine Learning Engineer with 4 years specializing in NLP and deep learning. '
            'Experience fine-tuning large language models and building production AI systems.\n\n'
            'EXPERIENCE\n'
            'ML Engineer, Freshworks (2021–Present)\n'
            '  • Fine-tuned BERT and RoBERTa for customer intent classification (89% accuracy)\n'
            '  • Built Named Entity Recognition pipeline for contract parsing\n'
            '  • Deployed models on GCP Vertex AI with A/B traffic splitting\n'
            '  • MLflow experiment tracking and model versioning\n\n'
            'Research Engineer, IIT Madras (2019–2021)\n'
            '  • Published 2 papers on transformer-based text summarization\n'
            '  • PyTorch-based training on distributed GPU clusters\n'
            '  • Hugging Face Transformers, Datasets libraries\n\n'
            'SKILLS\nPyTorch, TensorFlow, Python, Transformers, BERT, GPT, '
            'NLP, Text Classification, Named Entity Recognition, '
            'Computer Vision, OpenCV, MLflow, GCP Vertex AI, '
            'Hugging Face, Scikit-learn, Pandas, NumPy, CUDA\n\n'
            'EDUCATION\nM.Tech Artificial Intelligence — IIT Madras (2019)\n'
            'B.Tech Computer Science — Anna University (2017)\n'
        ),
        'skills': [
            ('PyTorch', 'technical', 5),
            ('TensorFlow', 'technical', 4),
            ('Python', 'technical', 5),
            ('NLP', 'technical', 5),
            ('BERT', 'technical', 5),
            ('Transformers', 'technical', 5),
            ('Machine Learning', 'technical', 5),
            ('Deep Learning', 'technical', 5),
            ('Computer Vision', 'technical', 3),
            ('MLflow', 'technical', 4),
            ('GCP', 'technical', 3),
            ('Hugging Face', 'technical', 5),
            ('Scikit-learn', 'technical', 4),
            ('Research', 'domain', 5),
            ('Communication', 'soft', 4),
        ],
    },
    {
        'username': 'demo_karan_shah',
        'first_name': 'Karan',
        'last_name': 'Shah',
        'email': 'karan.shah@demo.skillsevak',
        'profile': {
            'full_name': 'Karan Shah',
            'phone': '+91 96543 21098',
            'location': 'Ahmedabad, Gujarat',
            'experience_years': 8,
            'education_level': 'bachelor',
            'education_field': 'Computer Engineering',
            'salary_expectation': 2800000,
            'open_to_work': True,
        },
        'summary': (
            'Cloud Architect with 8 years designing multi-region AWS and GCP solutions. '
            'Certified AWS Solutions Architect Professional. Led cloud migration saving ₹4Cr/yr.'
        ),
        'resume_text': (
            'Karan Shah — Cloud Solutions Architect, Ahmedabad\n\n'
            'SUMMARY\nCloud Architect with 8 years designing and delivering enterprise-grade '
            'cloud solutions on AWS and GCP. AWS Certified Solutions Architect Professional. '
            'Expert in microservices, serverless, and multi-cloud strategies.\n\n'
            'EXPERIENCE\n'
            'Lead Cloud Architect, Adani Digital Labs (2019–Present)\n'
            '  • Architected multi-region AWS solution for 10M users\n'
            '  • Led migration of 150 on-prem services to AWS, saving ₹4Cr/year\n'
            '  • Terraform IaC for 40+ production environments\n'
            '  • Serverless architecture with Lambda, API Gateway, DynamoDB\n\n'
            'Senior Cloud Engineer, Deloitte (2017–2019)\n'
            '  • AWS Well-Architected Reviews for 12 enterprise clients\n'
            '  • GCP BigQuery and Dataflow for analytics pipelines\n'
            '  • Cost optimization saving clients $2M+ annually\n\n'
            'Cloud Engineer, Cognizant (2016–2017)\n'
            '  • EC2, RDS, S3, CloudFront, Route53 management\n\n'
            'SKILLS\nAWS, GCP, Azure, Terraform, CloudFormation, '
            'Kubernetes, Docker, Lambda, Serverless, Microservices, '
            'DynamoDB, RDS, S3, CloudFront, VPC, IAM, '
            'Python, Bash, Infrastructure as Code, Cost Optimization\n\n'
            'EDUCATION\nB.E. Computer Engineering — Gujarat University (2016)\n'
            'AWS Solutions Architect Professional (2021)\n'
        ),
        'skills': [
            ('AWS', 'technical', 5),
            ('GCP', 'technical', 4),
            ('Azure', 'technical', 3),
            ('Terraform', 'technical', 5),
            ('CloudFormation', 'technical', 5),
            ('Kubernetes', 'technical', 4),
            ('Docker', 'technical', 4),
            ('Serverless', 'technical', 5),
            ('Microservices', 'technical', 5),
            ('DynamoDB', 'technical', 4),
            ('Python', 'technical', 3),
            ('Bash', 'technical', 4),
            ('Cloud Architecture', 'domain', 5),
            ('Cost Optimization', 'domain', 5),
            ('Stakeholder Management', 'soft', 4),
        ],
    },
    {
        'username': 'demo_divya_nair',
        'first_name': 'Divya',
        'last_name': 'Nair',
        'email': 'divya.nair@demo.skillsevak',
        'profile': {
            'full_name': 'Divya Nair',
            'phone': '+91 77654 32180',
            'location': 'Kochi, Kerala',
            'experience_years': 3,
            'education_level': 'bachelor',
            'education_field': 'Statistics',
            'salary_expectation': 900000,
            'open_to_work': True,
        },
        'summary': (
            'Data Analyst with 3 years transforming raw data into actionable insights. '
            'Built Tableau dashboards that reduced executive reporting time by 5 hours/week.'
        ),
        'resume_text': (
            'Divya Nair — Data Analyst, Kochi\n\n'
            'SUMMARY\nData Analyst with 3 years turning complex datasets into clear business '
            'insights. Expert in SQL, Python, and data visualization with Tableau and Power BI.\n\n'
            'EXPERIENCE\n'
            'Data Analyst, KPMG India (2022–Present)\n'
            '  • Designed Tableau dashboards for C-suite financial reporting\n'
            '  • Complex SQL queries on multi-million row datasets in Redshift\n'
            '  • Python automation saving 5 hours/week of manual reporting\n'
            '  • A/B test analysis for marketing campaigns (uplift modeling)\n\n'
            'Business Analyst, Muthoot Finance (2021–2022)\n'
            '  • Power BI reports for loan portfolio analysis\n'
            '  • Excel VBA macros for data cleaning pipelines\n'
            '  • Customer segmentation with K-means clustering\n\n'
            'SKILLS\nSQL, Python, Tableau, Power BI, Excel, '
            'Pandas, NumPy, Matplotlib, Seaborn, '
            'AWS Redshift, BigQuery, Snowflake, '
            'Statistics, A/B Testing, Data Visualization, '
            'Business Intelligence, Reporting, Communication\n\n'
            'EDUCATION\nB.Sc. Statistics — Kerala University (2021)\n'
        ),
        'skills': [
            ('SQL', 'technical', 5),
            ('Python', 'technical', 4),
            ('Tableau', 'technical', 5),
            ('Power BI', 'technical', 4),
            ('Excel', 'technical', 5),
            ('Pandas', 'technical', 4),
            ('NumPy', 'technical', 3),
            ('Matplotlib', 'technical', 4),
            ('Redshift', 'technical', 3),
            ('BigQuery', 'technical', 3),
            ('Data Visualization', 'domain', 5),
            ('Business Intelligence', 'domain', 5),
            ('Statistics', 'domain', 4),
            ('A/B Testing', 'domain', 4),
            ('Communication', 'soft', 5),
        ],
    },
    {
        'username': 'demo_amit_kumar',
        'first_name': 'Amit',
        'last_name': 'Kumar',
        'email': 'amit.kumar@demo.skillsevak',
        'profile': {
            'full_name': 'Amit Kumar',
            'phone': '+91 88976 54321',
            'location': 'Delhi, NCR',
            'experience_years': 2,
            'education_level': 'bachelor',
            'education_field': 'Computer Science',
            'salary_expectation': 900000,
            'open_to_work': True,
        },
        'summary': (
            'Backend Developer with 2 years building REST APIs in Python/Django. '
            'Migrated legacy monolith to microservices, cutting API response time by 50%.'
        ),
        'resume_text': (
            'Amit Kumar — Backend Developer, Delhi NCR\n\n'
            'SUMMARY\nBackend developer with 2 years building scalable REST APIs with '
            'Python/Django and Flask. Strong in database design and API optimization.\n\n'
            'EXPERIENCE\n'
            'Backend Developer, Paytm (2023–Present)\n'
            '  • REST APIs in Django REST Framework serving 100K daily requests\n'
            '  • PostgreSQL schema design and query optimization (50% faster)\n'
            '  • Redis caching reducing DB load by 65%\n'
            '  • JWT authentication and role-based access control\n\n'
            'Junior Developer, Zoho (2022–2023)\n'
            '  • Flask microservices for CRM integrations\n'
            '  • Celery async task queues with RabbitMQ\n'
            '  • Unit tests with pytest; 85% code coverage\n\n'
            'SKILLS\nPython, Django, Django REST Framework, Flask, '
            'PostgreSQL, MySQL, Redis, Celery, RabbitMQ, '
            'REST API, JWT, Docker, Git, pytest, '
            'Linux, Bash, AWS EC2, S3\n\n'
            'EDUCATION\nB.Tech Computer Science — Delhi Technological University (2022)\n'
        ),
        'skills': [
            ('Python', 'technical', 5),
            ('Django', 'technical', 5),
            ('Django REST Framework', 'technical', 5),
            ('Flask', 'technical', 4),
            ('PostgreSQL', 'technical', 4),
            ('MySQL', 'technical', 4),
            ('Redis', 'technical', 3),
            ('Celery', 'technical', 3),
            ('REST API', 'technical', 5),
            ('JWT', 'technical', 4),
            ('Docker', 'technical', 3),
            ('pytest', 'technical', 4),
            ('Git', 'technical', 4),
            ('AWS', 'technical', 2),
            ('Problem Solving', 'soft', 4),
        ],
    },
    {
        'username': 'demo_sneha_patel',
        'first_name': 'Sneha',
        'last_name': 'Patel',
        'email': 'sneha.patel@demo.skillsevak',
        'profile': {
            'full_name': 'Sneha Patel',
            'phone': '+91 90012 34567',
            'location': 'Surat, Gujarat',
            'experience_years': 5,
            'education_level': 'master',
            'education_field': 'Business Administration',
            'salary_expectation': 2000000,
            'open_to_work': True,
        },
        'summary': (
            'Product Manager with 5 years shipping B2B SaaS features from 0 to 1. '
            'Launched billing module generating ₹3Cr ARR at CleverTap.'
        ),
        'resume_text': (
            'Sneha Patel — Product Manager, Surat\n\n'
            'SUMMARY\nProduct Manager with 5 years driving product strategy and execution '
            'in B2B SaaS. Strong in user research, roadmapping, and cross-functional leadership.\n\n'
            'EXPERIENCE\n'
            'Senior Product Manager, CleverTap (2021–Present)\n'
            '  • Owned billing and pricing module generating ₹3Cr ARR\n'
            '  • 0-to-1 product launch for enterprise analytics dashboard\n'
            '  • Led cross-functional team of 8 engineers, 2 designers\n'
            '  • Defined OKRs; increased MAU by 35% YoY\n\n'
            'Product Manager, Meesho (2019–2021)\n'
            '  • Seller onboarding flow reducing drop-off by 40%\n'
            '  • A/B tests with statistical significance analysis\n'
            '  • PRD writing, user story mapping, sprint planning\n\n'
            'Business Analyst, Deloitte (2018–2019)\n'
            '  • Requirements gathering, stakeholder interviews\n\n'
            'SKILLS\nProduct Management, Roadmapping, Agile, Scrum, '
            'JIRA, Confluence, Figma, SQL, Google Analytics, '
            'Mixpanel, A/B Testing, User Research, OKRs, '
            'PRD Writing, Stakeholder Management, Go-to-Market\n\n'
            'EDUCATION\nMBA Product & Strategy — IIM Ahmedabad (2019)\n'
            'B.Com — Gujarat University (2017)\n'
        ),
        'skills': [
            ('Product Management', 'domain', 5),
            ('Roadmapping', 'domain', 5),
            ('Agile', 'domain', 5),
            ('Scrum', 'domain', 5),
            ('JIRA', 'technical', 5),
            ('Confluence', 'technical', 4),
            ('Figma', 'technical', 4),
            ('SQL', 'technical', 3),
            ('Google Analytics', 'technical', 4),
            ('Mixpanel', 'technical', 4),
            ('A/B Testing', 'domain', 4),
            ('User Research', 'domain', 5),
            ('OKRs', 'domain', 5),
            ('Stakeholder Management', 'soft', 5),
            ('Leadership', 'soft', 5),
        ],
    },
    {
        'username': 'demo_vikram_singh',
        'first_name': 'Vikram',
        'last_name': 'Singh',
        'email': 'vikram.singh@demo.skillsevak',
        'profile': {
            'full_name': 'Vikram Singh',
            'phone': '+91 95432 10987',
            'location': 'Jaipur, Rajasthan',
            'experience_years': 4,
            'education_level': 'bachelor',
            'education_field': 'Electronics and Communication',
            'salary_expectation': 1300000,
            'open_to_work': True,
        },
        'summary': (
            'Android Developer with 4 years building high-rated apps (4.7★ on Play Store). '
            'Expertise in Kotlin, Jetpack Compose, and offline-first architecture at Juspay.'
        ),
        'resume_text': (
            'Vikram Singh — Android Developer, Jaipur\n\n'
            'SUMMARY\nAndroid Developer with 4 years building high-performance mobile apps. '
            'Expert in Kotlin, Jetpack Compose, and MVVM architecture. '
            'Published 3 apps with 500K+ combined downloads.\n\n'
            'EXPERIENCE\n'
            'Android Developer, Juspay (2021–Present)\n'
            '  • Payments SDK in Kotlin used by 50+ partner apps\n'
            '  • Jetpack Compose UI migration improving performance by 30%\n'
            '  • Offline-first architecture with Room and WorkManager\n'
            '  • Coroutines and Flow for async data streams\n\n'
            'Android Developer, InMobi (2020–2021)\n'
            '  • Mobile advertising SDK in Java/Kotlin\n'
            '  • Firebase Analytics, Crashlytics integration\n'
            '  • Google Play Store optimization (ASO)\n\n'
            'SKILLS\nKotlin, Java, Android SDK, Jetpack Compose, '
            'MVVM, Room, Retrofit, Coroutines, Flow, '
            'Firebase, Hilt/Dagger, WorkManager, '
            'REST API, Git, Android Studio, Gradle, '
            'Unit Testing, Mockito, Espresso\n\n'
            'EDUCATION\nB.Tech ECE — Rajasthan Technical University (2020)\n'
        ),
        'skills': [
            ('Kotlin', 'technical', 5),
            ('Java', 'technical', 4),
            ('Android SDK', 'technical', 5),
            ('Jetpack Compose', 'technical', 5),
            ('MVVM', 'technical', 5),
            ('Room', 'technical', 4),
            ('Retrofit', 'technical', 4),
            ('Coroutines', 'technical', 4),
            ('Firebase', 'technical', 4),
            ('Hilt', 'technical', 4),
            ('REST API', 'technical', 4),
            ('Git', 'technical', 4),
            ('Mobile Development', 'domain', 5),
            ('Unit Testing', 'technical', 4),
            ('Problem Solving', 'soft', 4),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed 10 diverse open-to-work demo candidates for Passive Talent Discovery'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo candidates and recreate them',
        )

    def handle(self, *args, **options):
        if options['reset']:
            deleted = 0
            for c in DEMO_CANDIDATES:
                try:
                    u = User.objects.get(username=c['username'])
                    u.delete()
                    deleted += 1
                except User.DoesNotExist:
                    pass
            self.stdout.write(self.style.WARNING(f'Deleted {deleted} existing demo candidates.'))

        created = 0
        skipped = 0

        for c in DEMO_CANDIDATES:
            if User.objects.filter(username=c['username']).exists():
                skipped += 1
                self.stdout.write(f"  SKIP  {c['profile']['full_name']} (already exists)")
                continue

            # 1. Create User
            user = User.objects.create_user(
                username=c['username'],
                email=c['email'],
                password='demo1234',
                first_name=c['first_name'],
                last_name=c['last_name'],
            )

            # 2. Create CandidateProfile
            p = c['profile']
            profile = CandidateProfile.objects.create(
                user=user,
                full_name=p['full_name'],
                phone=p['phone'],
                location=p['location'],
                experience_years=p['experience_years'],
                education_level=p['education_level'],
                education_field=p['education_field'],
                salary_expectation=p.get('salary_expectation'),
                open_to_work=p.get('open_to_work', True),
                skills=json.dumps([s[0] for s in c['skills'][:5]]),
                profile_strength=75,
            )

            # 3. Create ParsedResume with resume text
            ParsedResume.objects.create(
                candidate=profile,
                raw_text=c['resume_text'],
                cleaned_text=c['resume_text'].strip(),
                sections_json={'summary': c['summary'], 'skills': [s[0] for s in c['skills']]},
                parsing_status='completed',
                parsed_at=timezone.now(),
            )

            # 4. Create CandidateSkill records
            for skill_text, category, proficiency in c['skills']:
                CandidateSkill.objects.get_or_create(
                    candidate=profile,
                    normalized_text=skill_text.lower().strip(),
                    defaults={
                        'skill_text': skill_text,
                        'proficiency_level': proficiency,
                        'category': category,
                        'source': 'skills_section',
                        'confidence_score': 0.95,
                    },
                )

            created += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'  CREATE {p["full_name"]:20s} '
                    f'{p["experience_years"]}y · {p["education_level"]:10s} · '
                    f'{len(c["skills"])} skills'
                )
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Created: {created}  Skipped: {skipped}'
        ))
        if created > 0:
            self.stdout.write(
                'All demo candidates have open_to_work=True. '
                'Login as recruiter and open any job -> Recommended tab.'
            )
