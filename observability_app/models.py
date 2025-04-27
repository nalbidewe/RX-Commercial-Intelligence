from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ENUM, ARRAY
from sqlalchemy import text
from datetime import datetime

db = SQLAlchemy()

# User model
class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Text, primary_key=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta = db.Column("metadata", db.JSON, nullable=False)
    identifier = db.Column(db.Text, unique=True, nullable=False)
    # Relationship to threads
    threads = db.relationship('Thread', backref='user', lazy=True)

# Thread model
class Thread(db.Model):
    __tablename__ = "Thread"
    id = db.Column(db.Text, primary_key=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = db.Column(db.DateTime)
    name = db.Column(db.Text)
    meta = db.Column("metadata", db.JSON, nullable=False)
    # New tags column
    tags = db.Column(ARRAY(db.Text), server_default=text("ARRAY[]::TEXT[]"), nullable=False)
    userId = db.Column(db.Text, db.ForeignKey("User.id"))
    # Relationships to steps and elements
    steps = db.relationship('Step', backref='thread', lazy=True)
    elements = db.relationship('Element', backref='thread', lazy=True)

# Step model
class Step(db.Model):
    __tablename__ = "Step"
    id = db.Column(db.Text, primary_key=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    parentId = db.Column(db.Text, db.ForeignKey("Step.id"))
    threadId = db.Column(db.Text, db.ForeignKey("Thread.id"))
    input = db.Column(db.Text)
    meta = db.Column("metadata", db.JSON, nullable=False)
    name = db.Column(db.Text)
    output = db.Column(db.Text)
    type = db.Column(
        ENUM('assistant_message', 'embedding', 'llm', 'retrieval', 'rerank', 'run', 'system_message', 'tool', 'undefined', 'user_message',
             name="StepType"),
        nullable=False
    )
    showInput = db.Column(db.Text, default='json')
    isError = db.Column(db.Boolean, default=False)
    startTime = db.Column(db.DateTime, nullable=False)
    endTime = db.Column(db.DateTime, nullable=False)
    # Relationships to elements and feedback
    elements = db.relationship('Element', backref='step', lazy=True)
    feedbacks = db.relationship('Feedback', backref='step', lazy=True)

# Element model
class Element(db.Model):
    __tablename__ = "Element"
    id = db.Column(db.Text, primary_key=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    threadId = db.Column(db.Text, db.ForeignKey("Thread.id"))
    stepId = db.Column(db.Text, db.ForeignKey("Step.id"))
    meta = db.Column("metadata", db.JSON, nullable=False)
    mime = db.Column(db.Text)
    name = db.Column(db.Text, nullable=False)
    objectKey = db.Column(db.Text)
    url = db.Column(db.Text)
    chainlitKey = db.Column(db.Text)
    display = db.Column(db.Text)
    size = db.Column(db.Text)
    language = db.Column(db.Text)
    page = db.Column(db.Integer)
    props = db.Column(db.JSON)

# Feedback model
class Feedback(db.Model):
    __tablename__ = "Feedback"
    id = db.Column(db.Text, primary_key=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    stepId = db.Column(db.Text, db.ForeignKey("Step.id"), nullable=True)
    name = db.Column(db.Text, nullable=False)
    value = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)