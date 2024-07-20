from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

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

        try:
            allocation_df = allocate_rooms(group_df, hostel_df)
        except Exception as e:
            flash(f'Error during allocation: {e}')
            return redirect(request.url)

        # Store the allocation DataFrame globally
        allocation_df_global = allocation_df

        return render_template('allocation.html', tables=[allocation_df.to_html(classes='data')])

    return render_template('index.html')

def allocate_rooms(group_df, hostel_df):
    allocation_df = pd.DataFrame(columns=['Group ID', 'Hostel Name', 'Room Number', 'Members Allocated'])
    for index, group in group_df.iterrows():
        hostel_room = find_suitable_hostel_room(group, hostel_df)
        if hostel_room is not None:
            new_row = pd.DataFrame({
                'Group ID': [group['Group ID']],
                'Hostel Name': [hostel_room['Hostel Name']],
                'Room Number': [hostel_room['Room Number']],
                'Members Allocated': [group['Members']]
            })
            allocation_df = pd.concat([allocation_df, new_row], ignore_index=True)
        else:
            # Handle the case where no suitable room is found
            new_row = pd.DataFrame({
                'Group ID': [group['Group ID']],
                'Hostel Name': ['Not Allocated'],
                'Room Number': ['N/A'],
                'Members Allocated': [group['Members']]
            })
            allocation_df = pd.concat([allocation_df, new_row], ignore_index=True)
    return allocation_df

def find_suitable_hostel_room(group, hostel_df):
    filtered_hostel_df = hostel_df[(hostel_df['Gender'] == group['Gender']) & (hostel_df['Capacity'] >= group['Members'])]
    filtered_hostel_df = filtered_hostel_df.sort_values(by='Capacity')
    return filtered_hostel_df.iloc[0] if not filtered_hostel_df.empty else None

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
