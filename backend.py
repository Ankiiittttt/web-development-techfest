from flask import Flask, request, render_template, send_file, flash, redirect, url_for
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necessary for flashing messages

# Global variable to store the allocation DataFrame
allocation_df_global = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global allocation_df_global
    if request.method == 'POST':
        if 'group_csv' not in request.files or 'hostel_csv' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        group_csv = request.files['group_csv']
        hostel_csv = request.files['hostel_csv']

        if group_csv.filename == '' or hostel_csv.filename == '':
            flash('No selected file')
            return redirect(request.url)

        try:
            group_df = pd.read_csv(group_csv)
            hostel_df = pd.read_csv(hostel_csv)
        except Exception as e:
            flash(f'Error reading CSV files: {e}')
            return redirect(request.url)

        allocation_df = allocate_rooms(group_df, hostel_df)

        if allocation_df.empty:
            flash('No suitable rooms found for the given groups.')
            return redirect(request.url)

        # Store the allocation DataFrame globally
        allocation_df_global = allocation_df

        return render_template('allocation.html', tables=[allocation_df.to_html(classes='data')])

    return render_template('index.html')

def allocate_rooms(group_df, hostel_df):
    allocation_df = pd.DataFrame(columns=['Group ID', 'Hostel Name', 'Room Number', 'Members Allocated'])

    for index, group in group_df.iterrows():
        hostel_rooms = find_suitable_hostel_room(group, hostel_df)
        if hostel_rooms is not None:
            for hostel_room in hostel_rooms:
                new_row = pd.DataFrame({
                    'Group ID': [group['Group ID']],
                    'Hostel Name': [hostel_room['Hostel Name']],
                    'Room Number': [hostel_room['Room Number']],
                    'Members Allocated': [hostel_room['Members Allocated']]
                })
                allocation_df = pd.concat([allocation_df, new_row], ignore_index=True)
                hostel_df = hostel_df.drop(hostel_room.name)
                group['Members'] -= hostel_room['Members Allocated']
                if group['Members'] <= 0:
                    break

    return allocation_df

def find_suitable_hostel_room(group, hostel_df):
    suitable_rooms = hostel_df[(hostel_df['Gender'] == group['Gender']) & (hostel_df['Capacity'] >= group['Members'])]
    if suitable_rooms.empty:
        suitable_rooms = hostel_df[(hostel_df['Gender'] == group['Gender']) & (hostel_df['Capacity'] < group['Members'])]
        if not suitable_rooms.empty:
            return suitable_rooms.sort_values(by='Capacity', ascending=False).iloc[0:1].to_dict('records')
    else:
        return suitable_rooms.sort_values(by='Capacity').iloc[0:1].to_dict('records')
    return None

@app.route('/download_allocation', methods=['GET'])
def download_allocation():
    global allocation_df_global
    if allocation_df_global is None:
        return "No allocation data available. Please go back and upload the files first.", 400

    csv_buffer = BytesIO()
    allocation_df_global.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return send_file(csv_buffer, as_attachment=True, download_name='final.csv', mimetype='text/csv')

if __name__ == '__main__':
    app.run(debug=True)
