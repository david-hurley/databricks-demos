# Turnaround Solution Accelerator

### Overview

##### What is Turnaround
In industry, a turnaround refers to a planned, periodic shutdown of a plant or industrial facility to perform maintenance, inspections, repairs, and upgrades. It is a critical process aimed at ensuring safety, compliance, and operational efficiency, often involving large teams and significant logistical coordination.

##### Cost of Turnaround
Turnarounds are often the highest-cost activity because they require halting production, deploying large specialized workforces, and executing complex tasks within tight timeframes. The combination of lost revenue from downtime and high expenditures on labor, equipment, and materials drives up the overall cost significantly.


##### Cost Risks of Turnaround
The risk of cost overrun is high in turnarounds due to the complexity and unpredictability of discovering additional issues once equipment is opened or inspected. Tight schedules, dependency on contractor performance, and coordination across multiple teams amplify the chance of delays and budget escalation.

##### Cost Reduction Through Better Planning
Accurate planning before a turnaround is critical to minimize downtime and therefore reduce cost overrun. 
- Historical inspection and repair reports help identify and prioritize high-risk assets
- IoT sensor data between last turnaround and now can help highlight operating conditions which may have accelerated equipment detioration, such as temperatures above design conditions leading to increased corrosion. 


### Turnaround Agentic Planning Tool

##### Overview
This solution accelerator leverages the Databricks Mosaic AI Agent Framework to deploy a focused agent that analyzes historical inspection reports and IoT sensor data, providing engineers with data-driven recommendations for prioritizing tasks in the upcoming turnaround.

##### Architecture
The system follows this flow:
1. An engineer initiates a request for assistance in planning the upcoming Turnaround for a specific plant and piece of equipment. 

2. The AI agent is equipped with two key tools: a vector search index containing historical inspection reports and access to IoT sensor data for each asset. 

3. The agent analyzes past inspection findings and identifies recent sensor anomalies—such as unusual temperature patterns—to recommend priority areas for Turnaround planning.

![Turnaround Solution Accelerator Architecture](./artifacts/architecture_diagram.png)

### Getting Started
1. Create a Git Folder pointing to - `https://github.com/david-hurley/databricks-demos`, use sparse checkout to fetch only `turnaround-agent` folder

2. Navigate to the `turnaround-agent` folder and open `00-setup`, follow the instructions in the Notebook

3. We are going to prototype in the Playground. This lets us test various models, system prompts, and get an idea how the tools perform. From the Playground we will export the code to create `agent.py`, this exported code can also be found as `01-agent-creation`. 

- If using the Free Edition choose `Meta Llama 3.1 405B Instruct`. 
- Select `Tools` dropdown and add the 3 Unity Catalog functions that were created and registered in `00-setup`. 
- Also add the vector search index created in `00-setup`. 

  ![Tool Selection Playground](./artifacts/tool_addition_playground.png)

- Add the below system prompt

  ```You are a highly experienced planning engineer at a major energy company, responsible for preparing equipment and asset Turnaround plans. For each request, carefully review historical inspection reports for signs of degradation or recurring issues. Also analyze IoT sensor data to identify any values that exceeded alarm thresholds, as these may signal urgent or unplanned maintenance needs due to factors like corrosion, overheating, or wear. Your goal is to provide clear, data-backed recommendations to help engineers prioritize repair and inspection tasks during the upcoming Turnaround.```

4. Ask the Playground Agent for help, try `Help me plan for Turnaround for Plant A and equipment heat exchangers`. You will see the Agent decide which tools to use and start reasoning. 

5. Once you are happy with testing you can select `Create Agent Notebook`. This will create a Notebook named `driver` in a new folder. Move this to your Gitfolder, you can use `01-agent-creation` for now.