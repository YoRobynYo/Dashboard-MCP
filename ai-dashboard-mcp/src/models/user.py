from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Agent(db.Model):
    """Model for AI agents registered with the MCP"""
    id = db.Column(db.String(100), primary_key=True)  # Unique agent identifier
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    endpoint = db.Column(db.String(500), nullable=False)  # Agent's API endpoint
    capabilities = db.Column(db.Text)  # JSON string of capabilities
    status = db.Column(db.String(50), default='inactive')  # active, inactive, error
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Agent {self.id}: {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'endpoint': self.endpoint,
            'capabilities': json.loads(self.capabilities) if self.capabilities else [],
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def set_capabilities(self, capabilities_list):
        """Set capabilities as JSON string"""
        self.capabilities = json.dumps(capabilities_list)

    def get_capabilities(self):
        """Get capabilities as Python list"""
        return json.loads(self.capabilities) if self.capabilities else []


class Task(db.Model):
    """Model for tasks managed by the MCP"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(100), unique=True, nullable=False)  # UUID for task
    agent_id = db.Column(db.String(100), db.ForeignKey('agent.id'), nullable=False)
    task_type = db.Column(db.String(100), nullable=False)
    parameters = db.Column(db.Text)  # JSON string of task parameters
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    result = db.Column(db.Text)  # JSON string of task result
    error_message = db.Column(db.Text)
    priority = db.Column(db.Integer, default=5)  # 1-10, lower is higher priority
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Relationship
    agent = db.relationship('Agent', backref=db.backref('tasks', lazy=True))

    def __repr__(self):
        return f'<Task {self.task_id}: {self.task_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'task_type': self.task_type,
            'parameters': json.loads(self.parameters) if self.parameters else {},
            'status': self.status,
            'result': json.loads(self.result) if self.result else None,
            'error_message': self.error_message,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def set_parameters(self, parameters_dict):
        """Set parameters as JSON string"""
        self.parameters = json.dumps(parameters_dict)

    def get_parameters(self):
        """Get parameters as Python dict"""
        return json.loads(self.parameters) if self.parameters else {}

    def set_result(self, result_dict):
        """Set result as JSON string"""
        self.result = json.dumps(result_dict)

    def get_result(self):
        """Get result as Python dict"""
        return json.loads(self.result) if self.result else None


class Configuration(db.Model):
    """Model for system configuration settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Configuration {self.key}>'

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class User(db.Model):
    """User model for authentication and preferences"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    preferences = db.Column(db.Text)  # JSON string of user preferences
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'preferences': json.loads(self.preferences) if self.preferences else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def set_preferences(self, preferences_dict):
        """Set preferences as JSON string"""
        self.preferences = json.dumps(preferences_dict)

    def get_preferences(self):
        """Get preferences as Python dict"""
        return json.loads(self.preferences) if self.preferences else {}

