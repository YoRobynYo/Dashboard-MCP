"""
MCP Agent Base Class

This module provides a base class for AI agents that want to register with the MCP system.
Agents can inherit from this class to get automatic registration, heartbeat, and task handling.
"""

import requests
import threading
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import json

class MCPAgent(ABC):
    """Base class for MCP-managed AI agents"""
    
    def __init__(self, agent_id: str, name: str, description: str, 
                 mcp_endpoint: str, agent_port: int = 5001,
                 capabilities: Optional[List[str]] = None):
        """
        Initialize the MCP Agent
        
        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name for the agent
            description: Description of what this agent does
            mcp_endpoint: URL of the MCP server (e.g., 'http://localhost:5000')
            agent_port: Port this agent will listen on
            capabilities: List of capabilities this agent provides
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.mcp_endpoint = mcp_endpoint
        self.agent_port = agent_port
        self.capabilities = capabilities or []
        self.is_running = False
        self.heartbeat_thread = None
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"MCPAgent-{agent_id}")
        
    def register_with_mcp(self) -> bool:
        """Register this agent with the MCP server"""
        try:
            registration_data = {
                'id': self.agent_id,
                'name': self.name,
                'description': self.description,
                'endpoint': f'http://localhost:{self.agent_port}',
                'capabilities': self.capabilities
            }
            
            response = requests.post(
                f"{self.mcp_endpoint}/api/mcp/agents",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 201:
                self.logger.info(f"Successfully registered with MCP server")
                return True
            else:
                self.logger.error(f"Failed to register with MCP: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"Error registering with MCP: {str(e)}")
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to MCP server"""
        try:
            response = requests.post(
                f"{self.mcp_endpoint}/api/mcp/agents/{self.agent_id}/heartbeat",
                timeout=5
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Heartbeat failed: {response.status_code}")
                
        except requests.RequestException as e:
            self.logger.warning(f"Heartbeat error: {str(e)}")
    
    def _heartbeat_loop(self):
        """Background thread for sending periodic heartbeats"""
        while self.is_running:
            self.send_heartbeat()
            time.sleep(30)  # Send heartbeat every 30 seconds
    
    def start_heartbeat(self):
        """Start the heartbeat thread"""
        if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
            self.is_running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            self.logger.info("Heartbeat thread started")
    
    def stop_heartbeat(self):
        """Stop the heartbeat thread"""
        self.is_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
            self.logger.info("Heartbeat thread stopped")
    
    def unregister_from_mcp(self):
        """Unregister this agent from the MCP server"""
        try:
            response = requests.delete(
                f"{self.mcp_endpoint}/api/mcp/agents/{self.agent_id}",
                timeout=10
            )
            
            if response.status_code == 204:
                self.logger.info("Successfully unregistered from MCP server")
            else:
                self.logger.warning(f"Unregistration response: {response.status_code}")
                
        except requests.RequestException as e:
            self.logger.error(f"Error unregistering from MCP: {str(e)}")
    
    def update_task_status(self, task_id: str, status: str, 
                          result: Optional[Dict[str, Any]] = None,
                          error_message: Optional[str] = None):
        """Update task status in MCP"""
        try:
            update_data = {'status': status}
            
            if result is not None:
                update_data['result'] = result
            if error_message is not None:
                update_data['error_message'] = error_message
            
            response = requests.put(
                f"{self.mcp_endpoint}/api/mcp/tasks/{task_id}/status",
                json=update_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Task {task_id} status updated to {status}")
            else:
                self.logger.error(f"Failed to update task status: {response.status_code}")
                
        except requests.RequestException as e:
            self.logger.error(f"Error updating task status: {str(e)}")
    
    @abstractmethod
    def execute_task(self, task_id: str, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task assigned by the MCP
        
        Args:
            task_id: Unique identifier for the task
            task_type: Type of task to execute
            parameters: Task parameters
            
        Returns:
            Dict containing the task result
        """
        pass
    
    @abstractmethod
    def get_supported_task_types(self) -> List[str]:
        """
        Return list of task types this agent can handle
        
        Returns:
            List of supported task type strings
        """
        pass
    
    def handle_task_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming task request from MCP
        
        Args:
            task_data: Task data from MCP
            
        Returns:
            Response dict
        """
        try:
            task_id = task_data.get('task_id')
            task_type = task_data.get('task_type')
            parameters = task_data.get('parameters', {})
            
            if not task_id or not task_type:
                return {'error': 'Missing task_id or task_type'}
            
            # Check if we support this task type
            if task_type not in self.get_supported_task_types():
                error_msg = f"Unsupported task type: {task_type}"
                self.update_task_status(task_id, 'failed', error_message=error_msg)
                return {'error': error_msg}
            
            # Update task status to running
            self.update_task_status(task_id, 'running')
            
            try:
                # Execute the task
                result = self.execute_task(task_id, task_type, parameters)
                
                # Update task status to completed
                self.update_task_status(task_id, 'completed', result=result)
                
                return {'status': 'completed', 'result': result}
                
            except Exception as e:
                error_msg = f"Task execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.update_task_status(task_id, 'failed', error_message=error_msg)
                return {'error': error_msg}
                
        except Exception as e:
            self.logger.error(f"Error handling task request: {str(e)}")
            return {'error': 'Internal agent error'}
    
    def start(self):
        """Start the agent (register with MCP and start heartbeat)"""
        if self.register_with_mcp():
            self.start_heartbeat()
            self.logger.info(f"Agent {self.agent_id} started successfully")
            return True
        else:
            self.logger.error(f"Failed to start agent {self.agent_id}")
            return False
    
    def stop(self):
        """Stop the agent (stop heartbeat and unregister from MCP)"""
        self.stop_heartbeat()
        self.unregister_from_mcp()
        self.logger.info(f"Agent {self.agent_id} stopped")


class SimpleFlaskAgent(MCPAgent):
    """
    A simple Flask-based agent that can be extended by specific AI agents
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flask_app = None
    
    def create_flask_app(self):
        """Create and configure Flask app for this agent"""
        from flask import Flask, request, jsonify
        from flask_cors import CORS
        
        app = Flask(f"agent-{self.agent_id}")
        CORS(app)
        
        @app.route('/execute', methods=['POST'])
        def execute_endpoint():
            """Endpoint for MCP to send tasks to this agent"""
            try:
                task_data = request.json
                result = self.handle_task_request(task_data)
                return jsonify(result)
            except Exception as e:
                self.logger.error(f"Error in execute endpoint: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'agent_id': self.agent_id,
                'name': self.name,
                'capabilities': self.capabilities
            })
        
        @app.route('/capabilities', methods=['GET'])
        def get_capabilities():
            """Get agent capabilities"""
            return jsonify({
                'agent_id': self.agent_id,
                'capabilities': self.capabilities,
                'supported_task_types': self.get_supported_task_types()
            })
        
        self.flask_app = app
        return app
    
    def run_flask_app(self):
        """Run the Flask app"""
        if not self.flask_app:
            self.create_flask_app()
        
        self.flask_app.run(
            host='0.0.0.0',
            port=self.agent_port,
            debug=False,
            threaded=True
        )

