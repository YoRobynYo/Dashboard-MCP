from flask import Blueprint, jsonify, request
from src.models.user import Agent, Task, Configuration, User, db
from datetime import datetime
import uuid
import requests
import logging

mcp_bp = Blueprint('mcp', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@mcp_bp.route('/agents', methods=['GET'])
def get_agents():
    """Get all registered agents"""
    agents = Agent.query.all()
    return jsonify([agent.to_dict() for agent in agents])

@mcp_bp.route('/agents', methods=['POST'])
def register_agent():
    """Register a new AI agent with the MCP"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['id', 'name', 'endpoint']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if agent already exists
        existing_agent = Agent.query.filter_by(id=data['id']).first()
        if existing_agent:
            return jsonify({'error': 'Agent with this ID already exists'}), 409
        
        # Create new agent
        agent = Agent(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            endpoint=data['endpoint'],
            status='active'
        )
        
        # Set capabilities if provided
        if 'capabilities' in data:
            agent.set_capabilities(data['capabilities'])
        
        db.session.add(agent)
        db.session.commit()
        
        logger.info(f"Agent {agent.id} registered successfully")
        return jsonify(agent.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error registering agent: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get specific agent details"""
    agent = Agent.query.get_or_404(agent_id)
    return jsonify(agent.to_dict())

@mcp_bp.route('/agents/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """Update agent information"""
    try:
        agent = Agent.query.get_or_404(agent_id)
        data = request.json
        
        # Update fields if provided
        if 'name' in data:
            agent.name = data['name']
        if 'description' in data:
            agent.description = data['description']
        if 'endpoint' in data:
            agent.endpoint = data['endpoint']
        if 'capabilities' in data:
            agent.set_capabilities(data['capabilities'])
        if 'status' in data:
            agent.status = data['status']
        
        agent.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Agent {agent_id} updated successfully")
        return jsonify(agent.to_dict())
        
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/agents/<agent_id>/heartbeat', methods=['POST'])
def agent_heartbeat(agent_id):
    """Update agent heartbeat to indicate it's alive"""
    try:
        agent = Agent.query.get_or_404(agent_id)
        agent.last_heartbeat = datetime.utcnow()
        agent.status = 'active'
        db.session.commit()
        
        return jsonify({'status': 'heartbeat_received'})
        
    except Exception as e:
        logger.error(f"Error processing heartbeat for agent {agent_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/agents/<agent_id>', methods=['DELETE'])
def unregister_agent(agent_id):
    """Unregister an agent"""
    try:
        agent = Agent.query.get_or_404(agent_id)
        
        # Cancel any pending tasks for this agent
        pending_tasks = Task.query.filter_by(agent_id=agent_id, status='pending').all()
        for task in pending_tasks:
            task.status = 'cancelled'
            task.error_message = 'Agent unregistered'
            task.completed_at = datetime.utcnow()
        
        db.session.delete(agent)
        db.session.commit()
        
        logger.info(f"Agent {agent_id} unregistered successfully")
        return '', 204
        
    except Exception as e:
        logger.error(f"Error unregistering agent {agent_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks with optional filtering"""
    try:
        # Get query parameters for filtering
        agent_id = request.args.get('agent_id')
        status = request.args.get('status')
        task_type = request.args.get('task_type')
        
        # Build query
        query = Task.query
        
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        if status:
            query = query.filter_by(status=status)
        if task_type:
            query = query.filter_by(task_type=task_type)
        
        # Order by priority (lower number = higher priority) and creation time
        tasks = query.order_by(Task.priority.asc(), Task.created_at.asc()).all()
        
        return jsonify([task.to_dict() for task in tasks])
        
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/tasks', methods=['POST'])
def create_task():
    """Create a new task for an agent"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['agent_id', 'task_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify agent exists and is active
        agent = Agent.query.filter_by(id=data['agent_id']).first()
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        if agent.status != 'active':
            return jsonify({'error': 'Agent is not active'}), 400
        
        # Create new task
        task = Task(
            task_id=str(uuid.uuid4()),
            agent_id=data['agent_id'],
            task_type=data['task_type'],
            priority=data.get('priority', 5),
            status='pending'
        )
        
        # Set parameters if provided
        if 'parameters' in data:
            task.set_parameters(data['parameters'])
        
        db.session.add(task)
        db.session.commit()
        
        logger.info(f"Task {task.task_id} created for agent {data['agent_id']}")
        return jsonify(task.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get specific task details"""
    task = Task.query.filter_by(task_id=task_id).first_or_404()
    return jsonify(task.to_dict())

@mcp_bp.route('/tasks/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """Update task status and result"""
    try:
        task = Task.query.filter_by(task_id=task_id).first_or_404()
        data = request.json
        
        # Update status
        if 'status' in data:
            old_status = task.status
            task.status = data['status']
            
            # Update timestamps based on status
            if data['status'] == 'running' and old_status == 'pending':
                task.started_at = datetime.utcnow()
            elif data['status'] in ['completed', 'failed', 'cancelled']:
                task.completed_at = datetime.utcnow()
        
        # Update result if provided
        if 'result' in data:
            task.set_result(data['result'])
        
        # Update error message if provided
        if 'error_message' in data:
            task.error_message = data['error_message']
        
        db.session.commit()
        
        logger.info(f"Task {task_id} status updated to {task.status}")
        return jsonify(task.to_dict())
        
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/tasks/<task_id>/execute', methods=['POST'])
def execute_task(task_id):
    """Execute a task by sending it to the appropriate agent"""
    try:
        task = Task.query.filter_by(task_id=task_id).first_or_404()
        
        if task.status != 'pending':
            return jsonify({'error': 'Task is not in pending status'}), 400
        
        agent = Agent.query.get(task.agent_id)
        if not agent or agent.status != 'active':
            return jsonify({'error': 'Agent not available'}), 400
        
        # Update task status to running
        task.status = 'running'
        task.started_at = datetime.utcnow()
        db.session.commit()
        
        # Prepare task payload for agent
        task_payload = {
            'task_id': task.task_id,
            'task_type': task.task_type,
            'parameters': task.get_parameters()
        }
        
        # Send task to agent (async in real implementation)
        try:
            response = requests.post(
                f"{agent.endpoint}/execute",
                json=task_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Task {task_id} sent to agent {agent.id}")
                return jsonify({'status': 'task_sent_to_agent'})
            else:
                # Update task status to failed
                task.status = 'failed'
                task.error_message = f"Agent returned status {response.status_code}"
                task.completed_at = datetime.utcnow()
                db.session.commit()
                return jsonify({'error': 'Agent execution failed'}), 500
                
        except requests.RequestException as e:
            # Update task status to failed
            task.status = 'failed'
            task.error_message = f"Failed to communicate with agent: {str(e)}"
            task.completed_at = datetime.utcnow()
            db.session.commit()
            return jsonify({'error': 'Failed to communicate with agent'}), 500
        
    except Exception as e:
        logger.error(f"Error executing task {task_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    try:
        # Count agents by status
        active_agents = Agent.query.filter_by(status='active').count()
        inactive_agents = Agent.query.filter_by(status='inactive').count()
        error_agents = Agent.query.filter_by(status='error').count()
        
        # Count tasks by status
        pending_tasks = Task.query.filter_by(status='pending').count()
        running_tasks = Task.query.filter_by(status='running').count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        failed_tasks = Task.query.filter_by(status='failed').count()
        
        status = {
            'agents': {
                'active': active_agents,
                'inactive': inactive_agents,
                'error': error_agents,
                'total': active_agents + inactive_agents + error_agents
            },
            'tasks': {
                'pending': pending_tasks,
                'running': running_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'total': pending_tasks + running_tasks + completed_tasks + failed_tasks
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/configuration', methods=['GET'])
def get_configurations():
    """Get all configuration settings"""
    configurations = Configuration.query.all()
    return jsonify([config.to_dict() for config in configurations])

@mcp_bp.route('/configuration', methods=['POST'])
def create_configuration():
    """Create a new configuration setting"""
    try:
        data = request.json
        
        if 'key' not in data or 'value' not in data:
            return jsonify({'error': 'Missing required fields: key, value'}), 400
        
        # Check if configuration already exists
        existing_config = Configuration.query.filter_by(key=data['key']).first()
        if existing_config:
            return jsonify({'error': 'Configuration with this key already exists'}), 409
        
        config = Configuration(
            key=data['key'],
            value=data['value'],
            description=data.get('description', '')
        )
        
        db.session.add(config)
        db.session.commit()
        
        return jsonify(config.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating configuration: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@mcp_bp.route('/configuration/<config_key>', methods=['PUT'])
def update_configuration(config_key):
    """Update a configuration setting"""
    try:
        config = Configuration.query.filter_by(key=config_key).first_or_404()
        data = request.json
        
        if 'value' in data:
            config.value = data['value']
        if 'description' in data:
            config.description = data['description']
        
        config.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(config.to_dict())
        
    except Exception as e:
        logger.error(f"Error updating configuration {config_key}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

