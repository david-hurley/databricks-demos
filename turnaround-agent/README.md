### Problem
Any company that is in a "heavy" industry (i.e. one where materials or energy is produced) must periodically take assets offline for equipment inspection, repair, and replacement. This is typically referred to as Turnaround. 

Companies that conduct Turnarounds know that this is often the highest cost activity. This is because repairs/replacement can be expensive and excess downtime of assets means loss revenue. 

To avoid large cost overruns, companies want to be as accurate in planning for Turnaround as possible. This means understanding what the state of equipment will be prior to going offline such that equipment and parts are procured in advance and trades are scheduled. 

One major challenge in planning for Turnaround is being able to understand any adverse operating conditions that a piece of equipment encountered between the last Turnaround and now. For example, previous inspection reports may make no mention of concerns around a piece of equipment but if the temperature of that equipment exceeded design conditions following last Turnaround there may be repairs needed. This can lead to costly unplanned repairs if not considered. 

### Turnaround Demo
This demo shows how to create, deploy, and evaluate a single-agent system using the Mosaic AI Agent Framework.

The flow is the following:
1. A engineer asks for help planning for the upcoming Turnaround at a specific plant and for a specific piece of equipment
2. The agent has access to two tools - a vector search index of past inspection reports and data from sensors on each piece of equipment
3. The agent will use past inspection information and look for any temperature anomalies to make suggestions on where to focus future Turnaround efforts

![](/Workspace/Users/david.hurley@databricks.com/turnaround-agent/turnaround-agent/artifacts/architecture_diagram.png)

##### Getting Started
1. Create a Git Folder pointing to - `https://github.com/david-hurley/databricks-demos`
2. Open `00-setup` and follow the instructions
3. Test the tools, system prompts, and models in the Databricks Playground
4. Export a Agent notebook template
