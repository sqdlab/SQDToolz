
import tkinter as tk
from tkinter import*
from tkinter import ttk

import os
import json
import sys

from numpy import isin

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
    class DashboardGroup:
        class ElemSimpleLabel:
            def __init__(self, parent):
                self.lbl = Label(parent, text = "", justify=LEFT)
                self.lbl.pack(side=LEFT)
            
            def set_text_col(self, text, bg_col):
                self.lbl['text'] = text
                self.lbl['bg'] = bg_col

        class ElemLabelListBox:
            def __init__(self, parent):
                self.frame = Frame(parent)
                self.frame.pack(side=LEFT)
                self.lbl = Label(self.frame, text="", justify=LEFT)
                self.lstbx = ListBoxScrollBar(self.frame)
            
            def set_text_col_list(self, text, bg_col, list_elems):
                self.lbl['text'] = text
                self.lbl['bg'] = bg_col
                self.lstbx.update_vals(list_elems)
                #
                self.frame.columnconfigure(0, weight=1)
                self.frame.rowconfigure(0, weight=0)
                self.frame.rowconfigure(1, weight=1)
                self.lbl.grid(row=0, column=0, sticky='news')
                self.lstbx.frame.grid(row=1, column=0, sticky='news')
        class ElemListBox:
            def __init__(self, parent):
                self.lstbx = ListBoxScrollBar(parent)
                self.lstbx.frame.pack(fill=BOTH, expand=1)
            
            def set_list(self, list_elems):
                self.lstbx.update_vals(list_elems)

        def __init__(self, root, group_name):
            self.entries = []
            self.frame = LabelFrame(master=root, text = group_name)
            ExperimentViewer.DashboardGroup.ElemSimpleLabel

        def _populate_elements(self, elem_type, num_elem):
            #Trim off any elements that are not of the given type...
            for cur_elem in self.entries:
                if not isinstance(cur_elem, elem_type):
                    while len(self.entries) > 0:
                        kill_elem = self.entries.pop(0)
                        kill_elem.pack_forget()
                    break

            while num_elem < len(self.entries) and len(self.entries) > 0:
                kill_elem = self.entries.pop(0)
                kill_elem.pack_forget()
            while num_elem > len(self.entries):
                self.entries += [elem_type(self.frame)]

        def set_simple_labels(self, cur_str_and_cols):
            self._populate_elements(ExperimentViewer.DashboardGroup.ElemSimpleLabel, len(cur_str_and_cols))
            for ind, cur_lbl in enumerate(cur_str_and_cols):
                self.entries[ind].set_text_col(cur_lbl[0], cur_lbl[1])

        def set_simple_label_list(self, cur_str_and_cols_list):
            self._populate_elements(ExperimentViewer.DashboardGroup.ElemLabelListBox, len(cur_str_and_cols_list))
            for ind, cur_lbl in enumerate(cur_str_and_cols_list):
                self.entries[ind].set_text_col_list(cur_lbl[0], cur_lbl[1], cur_lbl[2])

        def set_simple_list(self, cur_list):
            self._populate_elements(ExperimentViewer.DashboardGroup.ElemListBox, len(cur_list))
            for ind, cur_list in enumerate(cur_list):
                self.entries[ind].set_list(cur_list)
    
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

        self.pw_dash_LR_UI = PanedWindow(orient =tk.HORIZONTAL, master=self.parent_dashboard, sashwidth=3, bg = "#000077", bd = 0)
        self.frame_dash_left = Frame(master=self.pw_dash_LR_UI)
        frame_dash_right = Frame(master=self.pw_dash_LR_UI)
        self.pw_dash_LR_UI.add(self.frame_dash_left,stretch='always')
        self.pw_dash_LR_UI.add(frame_dash_right,stretch='always')
        #
        self.pw_dash_LR_UI.pack(expand = 1, fill ="both")

        #Create Dashboard Groups:
        self.dash_MWs = ExperimentViewer.DashboardGroup(frame_dash_right, "Microwave Sources")
        self.dash_WFMs = ExperimentViewer.DashboardGroup(frame_dash_right, "Waveforms")
        self.dash_VOLTs = ExperimentViewer.DashboardGroup(frame_dash_right, "Voltage Sources")
        
        frame_grp1 = Frame(master=frame_dash_right)
        self.dash_ATTENs = ExperimentViewer.DashboardGroup(frame_grp1, "Attenuators")
        self.dash_ATTENs.frame.pack(side=LEFT)
        self.dash_SWs = ExperimentViewer.DashboardGroup(frame_grp1, "Switches")
        self.dash_SWs.frame.pack(side=LEFT)

        frame_grp2 = Frame(master=frame_dash_right)
        self.dash_WFMTs = ExperimentViewer.DashboardGroup(frame_grp2, "Waveform Transformations")
        self.dash_WFMTs.frame.pack(side=LEFT)
        
        self.dash_MWs.frame.pack(side=TOP)
        self.dash_WFMs.frame.pack(side=TOP)
        frame_grp1.pack(side=TOP)
        self.dash_VOLTs.frame.pack(side=TOP)
        frame_grp2.pack(side=TOP)


        ###############################
        # VAR AND SPEC DISPLAY ON LHS #
        #
        self.pw_dash_VARSPEC = PanedWindow(orient =tk.VERTICAL, master=self.frame_dash_left, sashwidth=3, bg = "#000077", bd = 0)
        frame_var_spec_up = Frame(master=self.pw_dash_VARSPEC)
        frame_var_spec_down = Frame(master=self.pw_dash_VARSPEC)
        self.pw_dash_VARSPEC.add(frame_var_spec_up,stretch='always')
        self.pw_dash_VARSPEC.add(frame_var_spec_down,stretch='always')
        self.pw_dash_VARSPEC.pack(expand = 1, fill ="both")
        # frame_var_spec_up.pack(expand=1, fill="both")
        # frame_var_spec_down.pack(expand=1, fill="both")
        #
        self.dash_VARs = ExperimentViewer.DashboardGroup(frame_var_spec_up, "Variables")
        self.dash_VARs.frame.pack(expand=1, fill="both")
        #
        #
        lblFrm_specs = LabelFrame(frame_var_spec_down, text="Experiment Specifications")
        lblFrm_specs.pack(expand=1, fill="both")
        self.dash_SPECs = ttk.Treeview(lblFrm_specs, show=["tree"])
        self.dash_SPECs["columns"]=("#0",)
        self.dash_SPECs.column("#0", minwidth=0, stretch=tk.NO)
        # self.dash_SPECs.heading("#0",text="Experiment Specifications",anchor=tk.W)
        self.dash_SPECs.grid(row=0, column=0, sticky='news')
        dash_SPECs_sb = ttk.Scrollbar(lblFrm_specs, orient="vertical", command=self.dash_SPECs.yview)
        dash_SPECs_sb.grid(row=0, column=1, sticky='news')
        self.dash_SPECs.configure(yscrollcommand=dash_SPECs_sb.set)
        # self.trvw_expts.bind('<<TreeviewSelect>>', self._event_trvw_expts_selected)
        #
        lblFrm_specs.rowconfigure(0, weight=1)
        lblFrm_specs.columnconfigure(0, weight=1)
        lblFrm_specs.columnconfigure(1, weight=1)
        #################


        self.pw_main_LR_UI = PanedWindow(orient =tk.HORIZONTAL, master=self.parent_expt_comp, sashwidth=3, bg = "#000077", bd = 0)
        self.expts_frame_left = Frame(master=self.pw_main_LR_UI)
        frame_right = Frame(master=self.pw_main_LR_UI)
        self.pw_main_LR_UI.add(self.expts_frame_left,stretch='always')
        self.pw_main_LR_UI.add(frame_right,stretch='always')
        #
        self.pw_main_LR_UI.pack(expand = 1, fill ="both")

        self.trvw_expts = ttk.Treeview(self.expts_frame_left, show=["tree"])
        self.trvw_expts["columns"]=("#0",)
        self.trvw_expts.column("#0", width=150, minwidth=0, stretch=tk.NO)
        self.trvw_expts.heading("#0",text="Experiments",anchor=tk.W)
        self.trvw_expts.grid(row=0, column=0, sticky='news')
        self.trvw_expts.bind('<<TreeviewSelect>>', self._event_trvw_expts_selected)
        trvw_expts_sb = ttk.Scrollbar(self.expts_frame_left, orient="vertical", command=self.trvw_expts.yview)
        trvw_expts_sb.grid(row=0, column=1, sticky='news')
        self.trvw_expts.configure(yscrollcommand=trvw_expts_sb.set)
        #
        frm_btns = Frame(self.expts_frame_left)
        self.cur_sel_trvw = ''
        self.btn_open_file = Button(master=frm_btns, text ="Open Config", command = self._event_btn_open_file)
        self.btn_open_file.grid(row=0, column=0, sticky='ns')
        self.btn_open_folder = Button(master=frm_btns, text ="Open Folder", command = self._event_btn_open_folder)
        self.btn_open_folder.grid(row=0, column=1, sticky='ns')
        frm_btns.grid(row=1, column=0, columnspan=2, sticky='ns')
        frm_btns.rowconfigure(0, weight=1)
        frm_btns.columnconfigure(0, weight=1)
        frm_btns.columnconfigure(1, weight=1)
        #
        self.expts_frame_left.rowconfigure(0, weight=1)
        self.expts_frame_left.rowconfigure(1, weight=0)
        self.expts_frame_left.columnconfigure(0, weight=1)
        self.expts_frame_left.columnconfigure(1, weight=0)
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
                self.trvw_expts.insert(tree_folder_date, "end", text=cur_data_folder, tags=[cur_path_data])

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
            cur_wfms = []
            for cur_hal in data['HALs']:
                cur_str = ""
                cur_list = []
                for cur_key in cur_hal:
                    if isinstance(cur_hal[cur_key], str) or isinstance(cur_hal[cur_key], float) or isinstance(cur_hal[cur_key], int) or isinstance(cur_hal[cur_key], bool):
                        cur_str += f"{cur_key}: {self._get_units(cur_hal[cur_key])}\n"
                    elif cur_key == "WaveformSegments": #Custom processing for AWG waveforms...
                        # cur_str += "Segments:\n"
                        for cur_seg in cur_hal[cur_key]:
                            if "Value" in cur_seg:
                                ampl_val = self._get_units(cur_seg["Value"])
                            elif "Amplitude" in cur_seg:
                                ampl_val = self._get_units(cur_seg["Amplitude"])
                            else:
                                ampl_val = ""
                            #Trim the WFS_ in the Type...
                            cur_list += [f'\t{cur_seg["Name"]}, [{cur_seg["Type"][4:]}], {self._get_units(cur_seg["Duration"])}s, {ampl_val}\n']
                
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
                if cur_hal['Type'] == 'WaveformAWG':
                    cur_wfms += [(cur_str[:-1], col, cur_list)]    #:-1 is to remove the last \n

            cur_wfmts = []
            for cur_wfmt in data['WFMTs']:
                cur_str = ""
                for cur_key in cur_wfmt:
                    if isinstance(cur_wfmt[cur_key], str) or isinstance(cur_wfmt[cur_key], float) or isinstance(cur_wfmt[cur_key], int) or isinstance(cur_wfmt[cur_key], bool):
                        cur_str += f"{cur_key}: {cur_wfmt[cur_key]}\n"
                col = 'white'
                cur_wfmts += [(cur_str[:-1], col)]

            cur_elems_in_view = {self.dash_SPECs.item(child)['text'] : child for child in self.dash_SPECs.get_children()}
            self.dash_SPECs.column("#0", width=self.frame_dash_left.winfo_width(), minwidth=0, stretch=tk.NO)
            for cur_spec in data['SPECs']:
                if cur_spec['Name'] in cur_elems_in_view:
                    tree_cur_spec = cur_elems_in_view[cur_spec['Name']]
                else:
                    tree_cur_spec = self.dash_SPECs.insert("", "end", text=cur_spec['Name'])
                
                cur_attrs = {self.dash_SPECs.item(x)['tags'][0] : x for x in self.dash_SPECs.get_children(tree_cur_spec)}
                for cur_key in cur_spec['Entries']:
                    dest = cur_spec['Entries'][cur_key]['Destination']
                    if len(dest) > 0:
                        dest = f"({dest[0][1]}: {dest[0][0]})"
                    else:
                        dest = ""
                    cur_str = f"{cur_key}: {cur_spec['Entries'][cur_key]['Value']} {dest}"
                    if cur_key in cur_attrs:
                        self.dash_SPECs.item(cur_attrs[cur_key], text=cur_str, tags=[cur_key])
                    else:
                        self.dash_SPECs.insert(tree_cur_spec, "end", text=cur_str, tags=[cur_key])

            #Setup the dashboard of labels...
            self.dash_MWs.set_simple_labels(cur_mws)
            self.dash_VOLTs.set_simple_labels(cur_volts)
            self.dash_SWs.set_simple_labels(cur_sws)
            self.dash_ATTENs.set_simple_labels(cur_attens)
            self.dash_WFMs.set_simple_label_list(cur_wfms)
            self.dash_WFMTs.set_simple_labels(cur_wfmts)

            self.trvw_expts.column("#0", width=self.expts_frame_left.winfo_width(), minwidth=0, stretch=tk.NO)

            #Read JSON file for latest variables...
            file_state = self._path + "_last_vars.txt"
            if not os.path.isfile(file_state):
                continue
            try:    #Needs try-catch as the file may be written to while being read - abort/ignore if it's being updated...
                with open(file_state) as json_file:
                    data = json.load(json_file)
            except:
                continue

            cur_vars = []
            for cur_var in data:
                cur_vars += [f"{cur_var}: {self._get_units(data[cur_var]['Value'])}\n"]
            # self.dash_VARs.set_simple_labels([(cur_str[:-1], 'white')])
            self.dash_VARs.set_simple_list([cur_vars])

            try:
                self.root.update()
            except:
                #Application destroyed...
                return


    def _get_units(self, val):
        if isinstance(val, float):
            if val <= 0.0:
                return val

            thinspace = u"\u2009"
            def clip_val(value):
                return f'{value:.12g}'

            if val < 1e-6:
                return f'{clip_val(val*1e9)}{thinspace}n'
            if val < 1e-3:
                return f'{clip_val(val*1e6)}{thinspace}μ'
            if val < 1:
                return f'{clip_val(val*1e3)}{thinspace}m'
            if val < 1000:
                return val
            if val < 1e6:
                return f'{clip_val(val*1e-3)}{thinspace}k'
            if val < 1e9:
                return f'{clip_val(val*1e-6)}{thinspace}M'

            return f'{clip_val(val*1e-9)}{thinspace}G'
        else:
            return val


    def _create_dashboard_group(self, name):
        ret_dict = {
            'label_entries' : [],
            'frame' : LabelFrame(master=self.parent_dashboard, text = name)
        }
        ret_dict['frame'].pack()
        return ret_dict

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
    # ExperimentViewer(r'Z:\Data\EH_QuantumClock_V2\\').main_loop()
    ExperimentViewer(r'D:\WorkUQ\Other Projects\VNA Chevrons\\').main_loop()

