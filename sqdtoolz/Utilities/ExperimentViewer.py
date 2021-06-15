
import tkinter as tk
from tkinter import*
from tkinter import ttk

import os
import json
import sys

class ListBoxScrollBar:
    def __init__(self, parent_ui_element):
        self.frame = Frame(master=parent_ui_element)

        self.listbox = Listbox(self.frame, exportselection=0)
        self.listbox.grid(row=0, column=0, sticky="news")
        self.scrollbar = Scrollbar(self.frame)
        self.scrollbar.grid(row=0, column=1, sticky="nes")
        self.frame.columnconfigure(0, weight=1) #Listbox horizontally stretches to meet up with the scroll bar...
        self.frame.columnconfigure(1, weight=0) #Scroll bar stays the same size regardless of frame width...
        self.frame.rowconfigure(0, weight=1)

        for values in range(100): 
            self.listbox.insert(END, values)
        
        self.listbox.config(yscrollcommand = self.scrollbar.set)
        self.scrollbar.config(command = self.listbox.yview)

    def update_vals(self, list_vals, cols=None, select_index=-1, generate_selection_event=True):
        if select_index == -1:
            #Get current selection if applicable:
            cur_sel = [m for m in self.listbox.curselection()]
            #Select first element by default...
            if len(cur_sel) == 0:
                cur_sel = 0
            else:
                cur_sel = cur_sel[0]
        else:
            cur_sel = select_index

        #Clear listbox
        self.listbox.delete(0,'end')
        for values in list_vals:
            self.listbox.insert(END, values)
        
        #Colour the values if applicable:
        if cols != None:
            for ind in range(len(list_vals)):
                self.listbox.itemconfig(ind, foreground=cols[ind])
        #Select the prescribed element from above...
        self.listbox.select_set(cur_sel)
        if generate_selection_event:
            self.listbox.event_generate("<<ListboxSelect>>")

    def enable(self):
        self.listbox.configure(state='normal')
        # self.scrollbar.configure(state='normal')
    def disable(self):
        self.listbox.configure(state='disabled')
        # self.scrollbar.configure(state='disabled')

    def get_sel_val(self, get_index = False):
        if get_index:
            values = [m for m in self.listbox.curselection()]
        else:
            values = [self.listbox.get(m) for m in self.listbox.curselection()]
        if len(values) == 0:
            return -1
        else:
            return values[0]

    def select_index(self, index, generate_selection_event = True):
        #Clear selection
        self.listbox.selection_clear(0, END)
        #Select new item
        self.listbox.select_set(index)
        if generate_selection_event:
            self.listbox.event_generate("<<ListboxSelect>>")

    def modify_selected_index(self, new_text, generate_selection_event = False):
        if self.listbox.size() == 0:
            return
        cur_ind = self.get_sel_val(True)
        self.listbox.insert(cur_ind, new_text)
        self.listbox.delete(cur_ind+1)
        self.select_index(cur_ind, generate_selection_event)

class ExperimentViewer:
    def __init__(self, path):
        self.root = tk.Tk()
        self.root.wm_title("SQDToolz experiment visualisation tool")

        self._path = path

        tabControl = ttk.Notebook(self.root)        
        self.tab_dashboard = ttk.Frame(tabControl)
        self.tab_expt_comp = ttk.Frame(tabControl)
        tabControl.add(self.tab_expt_comp, text ='Browser')
        tabControl.add(self.tab_dashboard, text ='Dashboard')
        tabControl.pack(expand = 1, fill ="both")

        self.parent_dashboard = self.tab_dashboard
        self.parent_expt_comp = self.tab_expt_comp

        #Create Dashboard Groups:
        self.dash_MWs = self._create_dashboard_group("Microwave Sources")
        self.dash_ATTENs = self._create_dashboard_group("Attenuators")
        self.dash_VOLTs = self._create_dashboard_group("Voltage Sources")
        self.dash_SWs = self._create_dashboard_group("Switches")
        self.dash_WFMTs = self._create_dashboard_group("Waveform Transformations")
        self.dash_SPECs = self._create_dashboard_group("Experiment Specifications")

        self.pw_main_LR_UI = PanedWindow(orient =tk.HORIZONTAL, master=self.parent_expt_comp, sashwidth=3, bg = "#000077", bd = 0)
        frame_left = Frame(master=self.pw_main_LR_UI)
        frame_right = Frame(master=self.pw_main_LR_UI)
        self.pw_main_LR_UI.add(frame_left,stretch='always')
        self.pw_main_LR_UI.add(frame_right,stretch='always')
        #
        self.pw_main_LR_UI.pack(expand = 1, fill ="both")

        self.trvw_expts = ttk.Treeview(frame_left, show=["tree"])
        self.trvw_expts["columns"]=("#0",)
        self.trvw_expts.column("#0", width=150, minwidth=0, stretch=tk.NO)
        self.trvw_expts.heading("#0",text="Experiments",anchor=tk.W)
        self.trvw_expts.grid(row=0, column=0, columnspan=2, sticky='news')
        self.trvw_expts.bind('<<TreeviewSelect>>', self._event_trvw_expts_selected)
        #
        self.cur_sel_trvw = ''
        self.btn_open_file = Button(master=frame_left, text ="Open Config", command = self._event_btn_open_file)
        self.btn_open_file.grid(row=1, column=0, sticky='ns')
        self.btn_open_folder = Button(master=frame_left, text ="Open Folder", command = self._event_btn_open_folder)
        self.btn_open_folder.grid(row=1, column=1, sticky='ns')
        #
        frame_left.rowconfigure(0, weight=1)
        frame_left.rowconfigure(1, weight=0)
        frame_left.columnconfigure(0, weight=1)
        frame_left.columnconfigure(1, weight=1)
        #
        # frame_left.grid(row=0, column=0, sticky='news')

        self.comp_left = ""
        self.btn_comp_left = Button(master=frame_right, text ="Select Left", command = self._event_btn_comp_left)
        self.btn_comp_left.grid(row=0, column=0)
        self.lbl_comp_left = Label(master=frame_right, text = "", justify=LEFT)
        self.lbl_comp_left.grid(row=0, column=1)
        self.comp_right = ""
        self.btn_comp_right = Button(master=frame_right, text ="Select Right", command = self._event_btn_comp_right)
        self.btn_comp_right.grid(row=1, column=0)
        self.lbl_comp_right = Label(master=frame_right, text = "", justify=LEFT)
        self.lbl_comp_right.grid(row=1, column=1)
        #
        self.lstbx_comps = ListBoxScrollBar(frame_right)
        self.lstbx_comps.frame.grid(row=2, column=0, columnspan=2, sticky='news')
        #
        frame_right.rowconfigure(0, weight=0)
        frame_right.rowconfigure(1, weight=0)
        frame_right.rowconfigure(2, weight=1)
        frame_right.columnconfigure(0, weight=0)
        frame_right.columnconfigure(1, weight=1)
        #
        # frame_right.grid(row=0, column=1, sticky='news')

        self.parent_expt_comp.rowconfigure(0, weight=1)
        self.parent_expt_comp.columnconfigure(0, weight=0)
        self.parent_expt_comp.columnconfigure(1, weight=1)
            

    def main_loop(self):
        self.pw_main_LR_UI.update()
        self.pw_main_LR_UI.sash_place(0, 110, 0)

        dirs = [x[0] for x in os.walk(self._path)]

        cur_date_folders = next(os.walk(self._path))[1]
        for cur_date_folder in cur_date_folders:
            tree_folder_date =self.trvw_expts.insert("", "end", text=cur_date_folder)

            cur_path_date = self._path + cur_date_folder
            cur_folders = next(os.walk(cur_path_date))[1]
            for cur_data_folder in cur_folders:
                # cur_sub_folders  = next(os.walk(cur_path_data))[1]
                cur_path_data = cur_path_date + '/' + cur_data_folder
                if not os.path.isfile(cur_path_data + "/laboratory_configuration.txt"):
                    continue
                self.trvw_expts.insert(tree_folder_date, "end", text=cur_data_folder, tags=cur_path_data)


        while True:
            #Read JSON file for latest configuration...
            file_state = self._path + "_last_state.txt"
            if not os.path.isfile(file_state):
                continue
            try:    #Needs try-catch as the file may be written to while being read - abort/ignore if it's being updated...
                with open(file_state) as json_file:
                    data = json.load(json_file)
            except:
                continue

            #Process the HALs...
            cur_mws = []
            cur_sws = []
            cur_volts = []
            cur_attens = []
            for cur_hal in data['HALs']:
                cur_str = ""
                for cur_key in cur_hal:
                    if isinstance(cur_hal[cur_key], str) or isinstance(cur_hal[cur_key], float) or isinstance(cur_hal[cur_key], int) or isinstance(cur_hal[cur_key], bool):
                        cur_str += f"{cur_key}: {cur_hal[cur_key]}\n"
                
                #Get state-colours based on the Output key...
                cur_on_key = ''
                if 'Output' in cur_hal:
                    cur_on_key = 'Output'
                elif 'output' in cur_hal:
                    cur_on_key = 'output'
                if cur_on_key != '':
                    if cur_hal[cur_on_key] == True or cur_hal[cur_on_key] == 'ON':
                        col = '#80ff80'
                    else:
                        col = '#ffafaf'
                else:
                    col = 'white'

                if cur_hal['Type'] == 'GENmwSource':
                    cur_mws += [(cur_str[:-1], col)]    #:-1 is to remove the last \n
                if cur_hal['Type'] == 'GENswitch':
                    cur_sws += [(cur_str[:-1], col)]    #:-1 is to remove the last \n
                if cur_hal['Type'] == 'GENvoltSource':
                    cur_volts += [(cur_str[:-1], col)]    #:-1 is to remove the last \n
                if cur_hal['Type'] == 'GENatten':
                    cur_attens += [(cur_str[:-1], col)]    #:-1 is to remove the last \n

            cur_wfmts = []
            for cur_wfmt in data['WFMTs']:
                cur_str = ""
                for cur_key in cur_wfmt:
                    if isinstance(cur_wfmt[cur_key], str) or isinstance(cur_wfmt[cur_key], float) or isinstance(cur_wfmt[cur_key], int) or isinstance(cur_wfmt[cur_key], bool):
                        cur_str += f"{cur_key}: {cur_wfmt[cur_key]}\n"
                col = 'white'
                cur_wfmts += [(cur_str[:-1], col)]

            cur_specs = []
            for cur_spec in data['SPECs']:
                cur_str = f"Name: {cur_spec['Name']}\n"
                for cur_key in cur_spec['Entries']:
                    dest = cur_spec['Entries'][cur_key]['Destination']
                    if len(dest) > 0:
                        dest = f"({dest[0][1]}: {dest[0][0]})"
                    else:
                        dest = ""
                    cur_str += f"{cur_key}: {cur_spec['Entries'][cur_key]['Value']} {dest}\n"
                col = 'white'
                cur_specs += [(cur_str[:-1], col)]

            #Setup the dashboard of labels...
            self._set_frame_labels(self.dash_MWs, cur_mws)
            self._set_frame_labels(self.dash_VOLTs, cur_volts)
            self._set_frame_labels(self.dash_SWs, cur_sws)
            self._set_frame_labels(self.dash_ATTENs, cur_attens)
            self._set_frame_labels(self.dash_WFMTs, cur_wfmts)
            self._set_frame_labels(self.dash_SPECs, cur_specs)
            
            
            self.trvw_expts

            try:
                self.root.update()
            except:
                #Application destroyed...
                return

    def _create_dashboard_group(self, name):
        ret_dict = {
            'label_entries' : [],
            'frame' : LabelFrame(master=self.parent_dashboard, text = name)
        }
        ret_dict['frame'].pack()
        return ret_dict

    def _set_frame_labels(self, dashboard_group, cur_str_and_cols):
        lbl_list = dashboard_group['label_entries']
        parent = dashboard_group['frame']
        while len(cur_str_and_cols) < len(lbl_list) and len(lbl_list) > 0:
            kill_lbl = lbl_list.pop(0)
            kill_lbl.pack_forget()
        while len(cur_str_and_cols) > len(lbl_list):
            new_lbl = Label(parent, text = "", justify=LEFT)
            new_lbl.pack(side=LEFT)
            lbl_list += [new_lbl]
        for ind, cur_lbl in enumerate(cur_str_and_cols):
            lbl_list[ind]['text'] = cur_lbl[0]
            lbl_list[ind]['bg'] = cur_lbl[1]


    def _event_trvw_expts_selected(self, event):
        for selected_item in self.trvw_expts.selection():
            # dictionary
            item = self.trvw_expts.item(selected_item)
            # list
            record = item['tags']
            if record == '':
                self.cur_sel_trvw = ''
                return
            #
            self.cur_sel_trvw = record[0]
    
    def _event_btn_open_file(self):
        if self.cur_sel_trvw != '' and os.path.isfile(self.cur_sel_trvw + "/laboratory_configuration.txt"):
            os.startfile(self.cur_sel_trvw + "/laboratory_configuration.txt")
    
    def _event_btn_open_folder(self):
        if self.cur_sel_trvw != '' and os.path.isdir(self.cur_sel_trvw):
            os.startfile(self.cur_sel_trvw)
    
    def _event_btn_comp_left(self):
        self.comp_left = self.cur_sel_trvw
        self.lbl_comp_left['text'] = f"Left: {self.comp_left[len(self._path):].replace('/',', ')}"
        self._compare_configs()
    
    def _event_btn_comp_right(self):
        self.comp_right = self.cur_sel_trvw
        self.lbl_comp_right['text'] = f"Right: {self.comp_right[len(self._path):].replace('/',', ')}"
        self._compare_configs()
    
    def _compare_configs(self):
        if self.comp_left == '' or not os.path.isdir(self.comp_left):
            return
        if self.comp_right == '' or not os.path.isdir(self.comp_right):
            return
        
        with open(self.comp_left + "/laboratory_configuration.txt") as json_file:
            data_left = json.load(json_file)
        with open(self.comp_right + "/laboratory_configuration.txt") as json_file:
            data_right = json.load(json_file)

        #Run through the Dictionaries
        list_vals = []
        list_vals += ["DIFFERENCES IN HALs"]
        list_vals += self._compare_dicts(data_left.get('HALs', {}), data_right.get('HALs', {}))
        list_vals += [" "]
        list_vals += ["DIFFERENCES IN PROCs"]
        list_vals += self._compare_dicts(data_left.get('PROCs', {}), data_right.get('PROCs', {}))
        list_vals += [" "]
        list_vals += ["DIFFERENCES IN WFMTs"]
        list_vals += self._compare_dicts(data_left.get('WFMTs', {}), data_right.get('WFMTs', {}))
        list_vals += [" "]
        list_vals += ["DIFFERENCES IN SPECs"]
        list_vals += self._compare_dicts(data_left.get('SPECs', {}), data_right.get('SPECs', {}))
        self.lstbx_comps.update_vals(list_vals)


    def _compare_dicts(self, list_left, list_right):
        list_vals = []
        while len(list_left) > 0:
            cur_dict = list_left.pop(0)
            #Find corresponding on the right-list if it exists
            right_comp = None
            for cur_right_dict_ind in range(len(list_right)):
                if cur_dict['Name'] == list_right[cur_right_dict_ind]['Name']:
                    right_comp = list_right.pop(cur_right_dict_ind)
                    break
            
            if right_comp == None:
                list_vals += [f"Killed {cur_dict['Name']}"]
            else:
                all_same = True
                for cur_key in cur_dict:
                    if cur_dict.get(cur_key, '') != right_comp.get(cur_key, ''):
                        if all_same:
                            list_vals += [cur_dict['Name']]
                            all_same = False
                        list_vals += [f"---{cur_key}: {cur_dict.get(cur_key, '')} → {right_comp.get(cur_key, '')}"]
        while len(list_right) > 0:
            right_comp = list_right.pop(0)
            list_vals += [f"Added {right_comp['Name']}"]
        
        return list_vals


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        print(sys.argv[1])
        ExperimentViewer(sys.argv[1]).main_loop()
    # ExperimentViewer('Z:/Data/sqdtoolz_test/').main_loop()

