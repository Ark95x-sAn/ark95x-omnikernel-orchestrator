# Agent Coordination Guide

## Overview

This guide explains how CrewAI agents coordinate within the ARK95X Omnikernel Orchestrator system, including collaboration patterns, communication protocols, and best practices for multi-agent workflows.

---

## Agent Types and Roles

### Specialized Agents

#### 1. Order Processing Agent
**Role**: Process and validate customer orders
**Capabilities**:
- Menu item validation
- Price calculation
- Order structuring
- Special request handling

**Tools**:
- Menu database lookup
- Pricing engine
- Inventory checker
- Allergen database

---

#### 2. Kitchen Coordination Agent
**Role**: Coordinate kitchen operations
**Capabilities**:
- Task assignment to stations
- Timing optimization
- Workflow sequencing
- Quality control

**Tools**:
- Station manager
- Timer/scheduler
- Recipe database
- Equipment status monitor

---

#### 3. Inventory Management Agent
**Role**: Monitor and manage inventory
**Capabilities**:
- Stock level tracking
- Demand forecasting
- Reorder automation
- Waste monitoring

**Tools**:
- Inventory database
- Analytics engine
- Supplier API
- Forecasting model

---

#### 4. Customer Service Agent
**Role**: Handle customer interactions
**Capabilities**:
- Query response
- Complaint resolution
- Recommendation generation
- Feedback collection

**Tools**:
- Knowledge base
- CRM system
- Sentiment analyzer
- Recommendation engine

---

#### 5. Analytics Agent
**Role**: Generate insights and reports
**Capabilities**:
- Trend analysis
- Performance metrics
- Revenue reporting
- Predictive analytics

**Tools**:
- Data warehouse
- Visualization tools
- Statistical models
- BI platform

---

## Collaboration Patterns

### Pattern 1: Sequential Processing

**Use Case**: Order fulfillment pipeline

```
Order Received
     ↓
Order Processing Agent
(validates and structures)
     ↓
Inventory Management Agent
(checks availability)
     ↓
Kitchen Coordination Agent
(schedules preparation)
     ↓
Customer Service Agent
(confirms with customer)
     ↓
Order Complete
```

**Implementation**:
```python
from crewai import Agent, Task, Crew

# Define agents
order_processor = Agent(
    role="Order Processor",
    goal="Validate and structure customer orders",
    tools=[menu_lookup, price_calculator]
)

inventory_manager = Agent(
    role="Inventory Manager",
    goal="Ensure ingredients are available",
    tools=[inventory_checker, reorder_system]
)

kitchen_coordinator = Agent(
    role="Kitchen Coordinator",
    goal="Schedule and coordinate preparation",
    tools=[station_manager, timer]
)

# Define tasks
process_order_task = Task(
    description="Process order: {order_data}",
    agent=order_processor,
    expected_output="Validated order structure"
)

check_inventory_task = Task(
    description="Verify ingredient availability for: {order_items}",
    agent=inventory_manager,
    expected_output="Availability confirmation",
    context=[process_order_task]  # Depends on order processing
)

schedule_preparation_task = Task(
    description="Schedule kitchen preparation for: {order_id}",
    agent=kitchen_coordinator,
    expected_output="Preparation schedule",
    context=[check_inventory_task]  # Depends on inventory check
)

# Create crew
order_crew = Crew(
    agents=[order_processor, inventory_manager, kitchen_coordinator],
    tasks=[process_order_task, check_inventory_task, schedule_preparation_task],
    process="sequential"
)

# Execute
result = order_crew.kickoff(inputs={'order_data': order})
```

---

### Pattern 2: Parallel Processing

**Use Case**: Multi-aspect analysis

```
                Customer Feedback
                       ↓
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  Sentiment     Quality        Service
  Analysis      Analysis       Analysis
  Agent         Agent          Agent
        │              │              │
        └──────────────┼──────────────┘
                       ▼
              Analytics Agent
              (consolidates)
                       ▼
              Final Report
```

**Implementation**:
```python
# Parallel analysis agents
sentiment_agent = Agent(
    role="Sentiment Analyzer",
    goal="Analyze customer sentiment",
    tools=[sentiment_model]
)

quality_agent = Agent(
    role="Quality Analyzer",
    goal="Evaluate food quality metrics",
    tools=[quality_metrics]
)

service_agent = Agent(
    role="Service Analyzer",
    goal="Assess service quality",
    tools=[service_metrics]
)

analytics_agent = Agent(
    role="Analytics Consolidator",
    goal="Consolidate all analyses",
    tools=[report_generator]
)

# Parallel tasks
sentiment_task = Task(
    description="Analyze sentiment in: {feedback}",
    agent=sentiment_agent
)

quality_task = Task(
    description="Evaluate quality from: {feedback}",
    agent=quality_agent
)

service_task = Task(
    description="Assess service from: {feedback}",
    agent=service_agent
)

# Consolidation task
consolidation_task = Task(
    description="Consolidate all analyses",
    agent=analytics_agent,
    context=[sentiment_task, quality_task, service_task]
)

# Create crew with parallel processing
analysis_crew = Crew(
    agents=[sentiment_agent, quality_agent, service_agent, analytics_agent],
    tasks=[sentiment_task, quality_task, service_task, consolidation_task],
    process="hierarchical"  # Enables parallel execution
)
```

---

### Pattern 3: Hierarchical Coordination

**Use Case**: Complex multi-stage operations

```
     Manager Agent
     (coordinates)
            ↓
    ┌───────┴────────┐
    ▼                ▼
Team Lead 1      Team Lead 2
    ↓                ↓
┌───┴───┐        ┌───┴───┐
▼       ▼        ▼       ▼
Agent1  Agent2   Agent3  Agent4
```

**Implementation**:
```python
# Manager agent
manager = Agent(
    role="Restaurant Manager",
    goal="Coordinate all restaurant operations",
    delegation=True  # Can delegate to other agents
)

# Team leads
kitchen_lead = Agent(
    role="Kitchen Team Lead",
    goal="Manage kitchen operations",
    delegation=True
)

service_lead = Agent(
    role="Service Team Lead",
    goal="Manage customer service",
    delegation=True
)

# Worker agents
prep_chef = Agent(role="Prep Chef", goal="Prepare ingredients")
line_cook = Agent(role="Line Cook", goal="Cook orders")
server = Agent(role="Server", goal="Serve customers")
host = Agent(role="Host", goal="Manage seating")

# Hierarchical crew
restaurant_crew = Crew(
    agents=[manager, kitchen_lead, service_lead, prep_chef, line_cook, server, host],
    tasks=[...],
    process="hierarchical",
    manager=manager  # Manager coordinates all
)
```

---

## Communication Protocols

### Agent-to-Agent Communication

#### 1. Direct Communication (Tool-based)
```python
from crewai.tools import tool

@tool("send_message_to_agent")
def send_message(recipient_agent_id: str, message: str) -> str:
    """
    Send a message to another agent

    Args:
        recipient_agent_id: ID of the receiving agent
        message: Message content

    Returns:
        Confirmation of message delivery
    """
    # Implementation
    message_queue.publish(recipient_agent_id, message)
    return f"Message sent to {recipient_agent_id}"


# Agent can use this tool
communicator_agent = Agent(
    role="Coordinator",
    tools=[send_message]
)
```

---

#### 2. Shared Context
```python
# Shared context object
class SharedContext:
    def __init__(self):
        self.order_status = {}
        self.inventory_levels = {}
        self.kitchen_capacity = {}

    def update_order_status(self, order_id: str, status: str):
        self.order_status[order_id] = status

    def get_order_status(self, order_id: str) -> str:
        return self.order_status.get(order_id, "unknown")


# Agents share context
shared_context = SharedContext()

agent1 = Agent(
    role="Agent 1",
    context=shared_context
)

agent2 = Agent(
    role="Agent 2",
    context=shared_context
)
```

---

#### 3. Event-Driven Communication
```python
from typing import Callable
import asyncio


class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    async def publish(self, event_type: str, data: dict):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                await callback(data)


# Usage
event_bus = EventBus()

# Agent 1 subscribes to events
async def handle_order_received(data):
    print(f"Processing order: {data['order_id']}")

event_bus.subscribe("order_received", handle_order_received)

# Agent 2 publishes events
await event_bus.publish("order_received", {"order_id": "ORD-123"})
```

---

## Coordination Strategies

### Load Balancing

```python
class LoadBalancer:
    def __init__(self, agents: list):
        self.agents = agents
        self.current_loads = {agent.id: 0 for agent in agents}

    def assign_task(self, task) -> Agent:
        """Assign task to least loaded agent"""
        least_loaded = min(self.agents, key=lambda a: self.current_loads[a.id])
        self.current_loads[least_loaded.id] += 1
        return least_loaded

    def complete_task(self, agent):
        """Mark task as complete, reduce load"""
        self.current_loads[agent.id] -= 1


# Usage
agents = [agent1, agent2, agent3]
load_balancer = LoadBalancer(agents)

for task in tasks:
    assigned_agent = load_balancer.assign_task(task)
    result = assigned_agent.execute(task)
    load_balancer.complete_task(assigned_agent)
```

---

### Priority Management

```python
from queue import PriorityQueue
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class PrioritizedTask:
    priority: int
    task: Any = field(compare=False)


class PriorityTaskManager:
    def __init__(self):
        self.queue = PriorityQueue()

    def add_task(self, task, priority: int):
        """Add task with priority (lower number = higher priority)"""
        self.queue.put(PrioritizedTask(priority, task))

    def get_next_task(self):
        """Get highest priority task"""
        if not self.queue.empty():
            return self.queue.get().task
        return None


# Usage
task_manager = PriorityTaskManager()

# Critical tasks
task_manager.add_task(urgent_order, priority=1)

# Normal tasks
task_manager.add_task(regular_order, priority=50)

# Low priority tasks
task_manager.add_task(analytics_task, priority=100)

# Process in priority order
while True:
    task = task_manager.get_next_task()
    if task:
        agent.execute(task)
```

---

### Conflict Resolution

```python
class ConflictResolver:
    """Resolve conflicts between agent decisions"""

    def resolve_resource_conflict(self, requests: list) -> dict:
        """
        Resolve conflicts when multiple agents want same resource

        Args:
            requests: List of resource requests with priorities

        Returns:
            Allocation decision
        """
        # Sort by priority
        sorted_requests = sorted(requests, key=lambda r: r['priority'])

        # Highest priority wins
        winner = sorted_requests[0]

        # Notify others
        for req in sorted_requests[1:]:
            self.notify_agent(req['agent_id'], 'request_denied', {
                'reason': 'higher_priority_request',
                'alternative': self.suggest_alternative(req)
            })

        return {
            'winner': winner['agent_id'],
            'resource': winner['resource_id']
        }
```

---

## Best Practices

### 1. Clear Role Definition
```python
# Good: Clear, specific role
agent = Agent(
    role="Kitchen Timer Manager",
    goal="Track and alert on cooking times for all active orders",
    backstory="Expert in time management with deep knowledge of cooking durations"
)

# Bad: Vague role
agent = Agent(
    role="Helper",
    goal="Help with stuff",
    backstory="Does things"
)
```

---

### 2. Appropriate Tool Assignment
```python
# Give agents only the tools they need
order_processor = Agent(
    role="Order Processor",
    tools=[
        menu_lookup,        # Needed
        price_calculator,   # Needed
        # NOT: kitchen_equipment_control - not needed
    ]
)
```

---

### 3. Error Handling in Coordination
```python
async def coordinate_agents(agents, task):
    """Coordinate multiple agents with error handling"""
    results = []
    errors = []

    for agent in agents:
        try:
            result = await agent.execute(task)
            results.append(result)
        except Exception as e:
            logger.error(f"Agent {agent.id} failed: {e}")
            errors.append({'agent': agent.id, 'error': str(e)})

            # Attempt recovery
            backup_agent = get_backup_agent(agent.role)
            if backup_agent:
                result = await backup_agent.execute(task)
                results.append(result)

    return {
        'results': results,
        'errors': errors,
        'success': len(errors) == 0
    }
```

---

### 4. State Management
```python
class AgentState:
    """Track agent state for coordination"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.status = "idle"  # idle, busy, error
        self.current_task = None
        self.last_update = None

    def start_task(self, task):
        self.status = "busy"
        self.current_task = task
        self.last_update = datetime.now()

    def complete_task(self):
        self.status = "idle"
        self.current_task = None
        self.last_update = datetime.now()

    def report_error(self, error):
        self.status = "error"
        self.last_error = error
        self.last_update = datetime.now()
```

---

### 5. Escalation in Multi-Agent Systems
```python
class MultiAgentEscalation:
    """Handle escalations in multi-agent environments"""

    def __init__(self, decision_router):
        self.decision_router = decision_router

    async def handle_agent_escalation(self, agent_id: str, issue: dict):
        """
        Handle when an agent needs to escalate

        Args:
            agent_id: Agent requesting escalation
            issue: Description of the issue
        """
        # Log escalation
        logger.info(f"Escalation from {agent_id}: {issue['type']}")

        # Route based on issue type
        if issue['type'] == 'capability_limit':
            # Find more capable agent
            return await self.decision_router.find_capable_agent(
                issue['required_capabilities']
            )

        elif issue['type'] == 'resource_unavailable':
            # Escalate to resource manager
            return await self.escalate_to_clone_manager(issue)

        elif issue['type'] == 'ambiguous_request':
            # Escalate to HLM-9 for interpretation
            return await self.escalate_to_hlm9(issue)

        else:
            # Unknown issue, escalate to orchestrator
            return await self.escalate_to_orchestrator(agent_id, issue)
```

---

## Monitoring Agent Coordination

### Metrics to Track

1. **Task Completion Rate**
   - Percentage of tasks completed successfully
   - Target: > 95%

2. **Average Task Duration**
   - Time from assignment to completion
   - Track per agent type

3. **Inter-Agent Communication**
   - Number of messages exchanged
   - Communication overhead

4. **Resource Utilization**
   - Agent busy/idle ratio
   - Target: 60-80% utilization

5. **Escalation Rate**
   - Percentage of tasks requiring escalation
   - Target: < 10%

### Monitoring Implementation

```python
class AgentCoordinationMonitor:
    """Monitor agent coordination metrics"""

    def __init__(self):
        self.metrics = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_duration': 0,
            'messages_sent': 0,
            'escalations': 0
        }

    def record_task_completion(self, agent_id: str, duration: float):
        self.metrics['tasks_completed'] += 1
        self.metrics['total_duration'] += duration

    def record_task_failure(self, agent_id: str, error: str):
        self.metrics['tasks_failed'] += 1
        logger.error(f"Task failed for {agent_id}: {error}")

    def record_message(self, from_agent: str, to_agent: str):
        self.metrics['messages_sent'] += 1

    def record_escalation(self, agent_id: str, reason: str):
        self.metrics['escalations'] += 1

    def get_metrics(self) -> dict:
        total_tasks = self.metrics['tasks_completed'] + self.metrics['tasks_failed']
        return {
            'completion_rate': self.metrics['tasks_completed'] / max(total_tasks, 1),
            'average_duration': self.metrics['total_duration'] / max(self.metrics['tasks_completed'], 1),
            'total_messages': self.metrics['messages_sent'],
            'escalation_rate': self.metrics['escalations'] / max(total_tasks, 1)
        }
```

---

## Troubleshooting

### Issue: Agents Not Coordinating

**Symptoms**:
- Tasks not being passed between agents
- Duplicate work
- Incomplete workflows

**Solutions**:
1. Verify task context is properly set
2. Check agent tool availability
3. Review delegation settings
4. Ensure shared state is accessible

---

### Issue: Deadlock

**Symptoms**:
- Agents waiting on each other
- Tasks stuck in queue
- No progress

**Solutions**:
1. Implement timeout on agent interactions
2. Add deadlock detection
3. Use asynchronous patterns
4. Break circular dependencies

---

### Issue: Poor Load Distribution

**Symptoms**:
- Some agents overloaded, others idle
- Uneven task completion times

**Solutions**:
1. Implement load balancing
2. Monitor agent capacity
3. Scale clone pool
4. Redistribute tasks

---

## Related Documentation

- [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)
- [Chain of Command](../chain-of-command/README.md)
- [Learning and Best Practices](./LEARNING_AND_BEST_PRACTICES.md)

---

**Version:** 1.0
**Last Updated:** 2025-11-19
**Maintained By:** ARK95X Core Team
