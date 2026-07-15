const userDefinedAuthorizedTags = {
	"pandemic": {
		"description": "From search: pandemic and visualization"
	},
	"visualization": {
		"description": "Visualization / visual analytics focus"
	},
	"healthcare": {
		"description": "From search: healthcare and visualization"
	},
	"epidemiological_modeling": {
		"description": "From search: epidemiological modeling and visualization"
	},
	"emergency_response": {
		"description": "From search: emergency response and visualization"
	},
	"pandemic_data": {
		"description": "Uses pandemic-related data (SurveyII classification)"
	},
	"domain_specific": {
		"description": "Domain-specific application (SurveyII Domain=1)"
	},
	"advanced_algorithms:no": {
		"description": "Survey II — Advanced Algorithm [0]: not using advanced algorithms"
	},
	"advanced_algorithms:yes": {
		"description": "Survey II — Advanced Algorithm [1]: using advanced algorithms for data processing and analysis"
	},
	"engagement:no": {
		"description": "Survey II — Public Engagement [0]: no need for dissemination"
	},
	"engagement:yes": {
		"description": "Survey II — Public Engagement [1]: need for dissemination / public engagement"
	},
	"size:author_small": {
		"description": "Survey II — Data Size [0]: author mentioned actual size as small"
	},
	"size:author_large": {
		"description": "Survey II — Data Size [1]: author mentioned size as above small / briefly as big data"
	},
	"size:estimated_small": {
		"description": "Survey II — Data Size [2]: observed & estimated as small (e.g. one-page table)"
	},
	"size:estimated_large": {
		"description": "Survey II — Data Size [3]: observed & estimated as above small size"
	},
	"data:tabular": {
		"description": "Tabular data"
	},
	"data:timeseries": {
		"description": "Time-series data"
	},
	"data:geospatial": {
		"description": "Geospatial data"
	},
	"data:spatiotemporal": {
		"description": "Spatiotemporal data"
	},
	"data:textual": {
		"description": "Textual / document data"
	},
	"data:document": {
		"description": "Document / text corpus data"
	},
	"data:event": {
		"description": "Event data"
	},
	"data:network": {
		"description": "Tree, set, graph/network data"
	},
	"data:imagery": {
		"description": "2D scalar field / imagery data"
	},
	"data:volume": {
		"description": "3D+ scalar field / volume data"
	},
	"data:video": {
		"description": "Video data"
	},
	"user:public": {
		"description": "Target users: general public"
	},
	"user:policymakers": {
		"description": "Target users: policymakers"
	},
	"user:domain_experts": {
		"description": "Target users: domain experts"
	},
	"user:public_health": {
		"description": "Target users: public health experts"
	},
	"user:data_scientists": {
		"description": "Target users: data scientists"
	},
	"user:epidemiologists": {
		"description": "Target users: epidemiologists"
	},
	"user:healthcare_experts": {
		"description": "Target users: healthcare experts"
	},
	"user:researchers": {
		"description": "Target users: researchers"
	},
	"interaction:basic": {
		"description": "Survey II — Level of Interaction: basic user–data interaction"
	},
	"interaction:medium": {
		"description": "Survey II — Level of Interaction: medium user–data interaction"
	},
	"interaction:advanced": {
		"description": "Survey II — Level of Interaction: advanced visual analytical interaction"
	},
	"interaction:static": {
		"description": "Survey II — Level of Interaction: static visualization"
	},
	"interaction:immersive": {
		"description": "Survey II — Level of Interaction: immersive visual analytics"
	},
	"tool:toolkits": {
		"description": "Survey II — Tools and Platforms: computational toolkits (e.g. Python, R)"
	},
	"tool:web_app": {
		"description": "Survey II — Tools and Platforms: web-based application"
	},
	"tool:software": {
		"description": "Survey II — Tools and Platforms: desktop/software tools (e.g. Tableau)"
	},
	"tool:mobile_app": {
		"description": "Survey II — Tools and Platforms: mobile application"
	},
	"tool:immersive_app": {
		"description": "Survey II — Tools and Platforms: immersive / XR application"
	},
	"visual:line": {
		"description": "Line chart"
	},
	"visual:bar": {
		"description": "Bar chart"
	},
	"visual:dashboard": {
		"description": "Dashboard"
	},
	"visual:map": {
		"description": "Map / geospatial view"
	},
	"visual:scatter": {
		"description": "Scatter plot"
	},
	"visual:heatmap": {
		"description": "Heatmap"
	},
	"visual:network": {
		"description": "Node-link / network graph"
	},
	"visual:wordcloud": {
		"description": "Word cloud"
	},
	"level:disseminative": {
		"description": "Disseminative visualization — communicate known facts"
	},
	"level:observational": {
		"description": "Observational visualization — explore and confirm patterns"
	},
	"level:analytical": {
		"description": "Analytical visualization — interactive analysis"
	},
	"level:model_developmental": {
		"description": "Model-developmental visualization — support modeling"
	},
	"task:visualize": {
		"description": "Primary task: visualize"
	},
	"task:analyze": {
		"description": "Primary task: analyze"
	},
	"task:model": {
		"description": "Primary task: model"
	},
	"task:understand": {
		"description": "Primary task: understand"
	}
}
