from dash import html, dcc


def create_layout():
    """Create and return the Dash app layout."""
    return html.Div([
        html.H1("Simple Dash App", style={'textAlign': 'center', 'marginBottom': '30px'}),
        
        # PostgreSQL Section
        html.Div([
            html.H2("PostgreSQL", style={'marginBottom': '20px'}),
            html.Div([
                dcc.Input(
                    id='name-input',
                    type='text',
                    placeholder='Enter name...',
                    style={
                        'padding': '10px',
                        'marginRight': '10px',
                    }
                ),
                dcc.Input(
                    id='email-input',
                    type='email',
                    placeholder='Enter email...',
                    style={
                        'padding': '10px',
                        'marginRight': '10px',
                    }
                ),
                html.Button(
                    'Write To Postgres',
                    id='write-button',
                    n_clicks=0,
                    style={
                        'padding': '10px 20px',
                    }
                ),
            ]),
            html.Div(id='write-status'),
            html.Div([
                html.Button(
                    'Read From Postgres',
                    id='refresh-button',
                    n_clicks=0,
                    style={
                        'padding': '10px 20px',
                        'marginBottom': '20px',
                        'marginTop': '20px'
                    }
                ),
            ]),
            html.Div(id='data-display')
        ], style={'marginBottom': '50px', 'paddingBottom': '30px', 'borderBottom': '2px solid #ddd'}),
        
        # Delta Lake Section
        html.Div([
            html.H2("Delta Lake", style={'marginBottom': '20px'}),
            html.Div([
                dcc.Input(
                    id='delta-name-input',
                    type='text',
                    placeholder='Enter name...',
                    style={
                        'padding': '10px',
                        'marginRight': '10px',
                    }
                ),
                dcc.Input(
                    id='delta-email-input',
                    type='email',
                    placeholder='Enter email...',
                    style={
                        'padding': '10px',
                        'marginRight': '10px',
                    }
                ),
                html.Button(
                    'Write to Delta',
                    id='delta-write-button',
                    n_clicks=0,
                    style={
                        'padding': '10px 20px',
                    }
                ),
            ]),
            html.Div(id='delta-write-status'),
            html.Div([
                html.Button(
                    'Read From Delta',
                    id='delta-read-button',
                    n_clicks=0,
                    style={
                        'padding': '10px 20px',
                        'marginBottom': '20px',
                        'marginTop': '20px'
                    }
                ),
            ]),
            html.Div(id='delta-data-display')
        ])
    ])

