import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session
import json

st.set_page_config(page_title="Table Editor", page_icon="📋", layout="wide")


def exec_sql(sess, query):
    try:
        rowset=sess.sql(query)       
    except Exception as e:
            st.error("Oops! ", query, "error executing", str(e), "occurred.")
            return pd.DataFrame()
    else:
        try:
            tdf = pd.DataFrame(rowset.collect())
        except Exception as e1:
                st.error(str(e1))
                return pd.DataFrame()
        else:
            return tdf
    return 



@st.cache_resource
def init_connection():
    try:
        session = get_active_session()
        
        return session
        
    except Exception as e:
        st.error("Connection Failed. Please try again! The pages will not work unless a succesfull connection is made" + '\n' + '\n' + "error: " + str(e))

@st.cache_data
def get_table_list(database,schema):
    try:        
        table_list_pk_sql = "show primary keys in schema " + database + "." + schema
        session.sql(table_list_pk_sql).collect()
        table_list_sql = 'SELECT "table_name" FROM table(RESULT_SCAN(LAST_QUERY_ID(-1))) group by "table_name" having sum(1) = 1 '
        table_list_df= session.sql(table_list_sql).to_pandas()        
        return table_list_df
    except Exception as e:
        st.sidebar.error("Sorry, An error occcured in get_table_list(): " + str(e))


@st.cache_data
def get_col_list_sql(tablel_name):
    try:
        col_list_sql = "SELECT LISTAGG('VALUE:' || COLUMN_NAME ||'::'||DATA_TYPE || ' AS ' || COLUMN_NAME , ',' )               \
                WITHIN GROUP ( ORDER BY  ORDINAL_POSITION) || ', VALUE:DEL::VARCHAR AS DEL'  COL_SELECT_FOR_JSON,                   \
                LISTAGG( CASE WHEN COLUMN_NAME = '" + PK_COL + "' THEN NULL ELSE  ' tgt.' || COLUMN_NAME || ' =  src.' || COLUMN_NAME END , ', ') \
            WITHIN GROUP ( ORDER BY  ORDINAL_POSITION)                                                                              \
            COL_LIST_FOR_MERGE_UPDATE,                                                                                              \
                '(' || LISTAGG(  COLUMN_NAME, ',')   WITHIN GROUP ( ORDER BY  ORDINAL_POSITION) || ')                               \
                    ' ||'VALUES (' ||  LISTAGG(  'src.' || COLUMN_NAME, ', ') WITHIN GROUP ( ORDER BY  ORDINAL_POSITION) || ')'     \
            COL_LIST_FOR_MERGE_INSERT                                                                                               \
            FROM INFORMATION_SCHEMA.COLUMNS                                                                                         \
            WHERE TABLE_NAME = '" + table_name + "';"

            #get one row row back with the 3 column lists 
            ##store each column list into its own  variable to be used later
        table_list_df = session.sql(col_list_sql).to_pandas()
        
        return table_list_df

        
    except Exception as e:
        st.sidebar.error("Sorry, An error occcured in  get_col_list_sql(): " + str(e))

@st.cache_data
def get_primary_keys (table_name):
    try:
        # for merging into a table we need to know which Column to merge on. We need to
        # check if a PK key exists and get its name    
        get_PK_sql = "show primary keys in " + table_name
        session.sql(get_PK_sql).collect()
        #because this is a show command we need to get the QueryID from the show command and execute again
        get_PK_sql = 'SELECT * FROM table(RESULT_SCAN(LAST_QUERY_ID(-1)))'
        pk_list_df = session.sql(get_PK_sql).to_pandas()
        #st.write(pk_list_df)
        return pk_list_df
    except Exception as e:
        st.sidebar.error("Sorry, An error occcured in get_primary_keys(): " + str(e))

def get_table_to_edit(table_name,PK_COL):
    try:
        select_stmt = "SELECT * FROM  " +  table_name + " ORDER BY " + PK_COL
        table_edit_df = session.sql(select_stmt).to_pandas()
        return table_edit_df
    except Exception as e:
        st.sidebar.error("Sorry, An error occcured in get_table_to_edit(): " + str(e))


##add some markdown to the page with a desc 
st.header("Let\'s get editing 📋")

##snowflake connection info. This will get read in from the values submitted on the homepage


try:
    session = init_connection()
    #open the connection

except Exception as e:
        st.error("Connection Failed.  Please try again! The pages will not work unless a sucessfull connection is made" + '\n' + '\n' + "error: " + str(e))

sf_database = session.get_current_database()
sf_schema = session.get_current_schema()

#sf_database = 'DEMODB'
#sf_schema = 'DEMO'


col1, col2, col3 = st.columns(3)
col1.header("Database")
col2.header("Schema")
col3.header("Tables")

dbs=exec_sql(session, "show databases")    
dbs=dbs[["name"]]
table_name=None
if not dbs.empty :
    selectdb = col1.selectbox('Select Database:', dbs)
    schemas=exec_sql(session, "show schemas in database "+selectdb)
    schemas=schemas[["name"]]
    
if  not schemas.empty :   
    selectschema = col2.selectbox('Select Schema:', schemas)
    sf_database=dbs
    sf_schema=schemas
    tables=exec_sql(session, "show primary keys in schema  "+selectdb+"."+selectschema)

if not tables.empty :
        tables=tables[["table_name"]]
        table_name = col3.selectbox('Select Table (Only display with on PK):', tables)     
        curr_table=sf_database+"."+sf_schema+"."+table_name
    
#TODO: parameters for table_updater(db,schema,table,sql_query,primary_key)
#display the select box with values from table dataframe
#st.write("Select the table you'd like to edit. Only valid tables with ONE primary key defined are shown.")

#formatting to contain the select box to only one column, so it doesnt span the entire width


if table_name:
    st.write("You selected: " +  table_name)
    results = get_primary_keys(table_name)

    #error handling logic to check if 1 and only 1 PK exists. If only 1 we stop 
    if len(results) != 1 :
        #formatting to contain the error to only one column, so it doesnt span the entire width
        with col1:
            st.error('Only tables with 1 PK column are supported: Your Table has less than 1 or more than 1 PK column')
    #otherwise we continue to process the table with a single PK
    else: 
        #get the PK name and store into a variable for later use    
        #st.write(results)
        PK_COL = results.iloc[0]['column_name']
                
        #get table to edit into dataframe
        df = get_table_to_edit(table_name,PK_COL)


        #make use of the new data frame editor as of 1.19 to allow edits to DF objects. 

        # num rows dynamic allows for INSERTS. if you would not like inserts remove this option
        # edited rsults get stored in the session_state of data_editor json object
        edited_df = st.experimental_data_editor(df, key="data_editor", use_container_width=True, num_rows="dynamic")
        
        ######## DEBUGGING ###########
        #  remove the next two lines to see output of changed DF ###### 
        # st.write("Here's the session state:")
        # st.write(st.session_state["data_editor"])
        ###### END DEBUGGING ######

        #save the session state into a variable
        json_raw = st.session_state["data_editor"]

        # create a submit button to hold the state until ready to process back to snowflake
        # this allows users to make many edits to the DF whily only submitting one merge request once complete
        submit =st.button("Save Data")

        col_list_df = get_col_list_sql(table_name)
        COL_SELECT_FOR_JSON = col_list_df.iloc[0]['COL_SELECT_FOR_JSON']
        COL_LIST_FOR_MERGE_UPDATE = col_list_df.iloc[0]['COL_LIST_FOR_MERGE_UPDATE']
        COL_LIST_FOR_MERGE_INSERT = col_list_df.iloc[0]['COL_LIST_FOR_MERGE_INSERT']

        #### DEBUGGING ##################
        #st.write(COL_SELECT_FOR_JSON)
        #st.write(COL_LIST_FOR_MERGE_UPDATE)
        #st.write(COL_LIST_FOR_MERGE_INSERT)
        # END DEBUGGING #############

        #create an empty dataframe to merge edits, inserts and delete DFs info 
        merged_df = pd.DataFrame()

        #when submit butten is clicked, we can begin processing the JSON state and create 3 dataframes for edits, inderts and delets. This will get dumpted to JSON
        if submit: 
            
            #loop through the session state JSON object
            for key in json_raw:
                value = json_raw[key]
                
            
                #handle edit and check is the edit has values 
                if key == "edited_cells" and  len(json_raw['edited_cells']) > 0:

                    #create a Dataframe from the JSON object 
                    edit_df = pd.DataFrame.from_dict(json_raw['edited_cells'], orient='index', columns=['VAL'])

                    edit_df.reset_index(inplace=True)
                    #the JSON gives us a : delmimited list. we will bring into two columns for row num and column number 
                    edit_df= edit_df.rename(columns={"index": "KEY"})
                    edit_df[['ROW','COL']] = edit_df.KEY.str.split(":",expand=True)
                    #we then need to pivit the rows and coumns to get the dataframe to look like structured data 
                    edit_df=edit_df.pivot(index='ROW', columns='COL', values='VAL')
                    #rename the columns from col Ids to column names from our orginal DF 
                    for col in edit_df.columns:
                        edit_df.rename(columns={str(col): df.columns[int(col)-1]}, inplace=True)
                    #remove multi-level index so we can perform merge 
                    edit_df.rename_axis(None, inplace=True)
                    edit_df.reset_index(inplace=True)
                    edit_df= edit_df.rename(columns={"index": "ROW"})
                    #convert row column to int, needed for merge operation
                    edit_df['ROW']=edit_df['ROW'].astype(int)
                    cols_to_merge= df.columns.difference(edit_df.columns)
                    #merge/join with orginal dataframe to get the column values that were changes 
                    edit_df = pd.merge(edit_df, df[cols_to_merge], left_on='ROW', right_index=True)
                    #remove the unneeded colunm
                    edit_df.drop(columns=['ROW'], inplace=True)
                    #add a column denoting this is not a delete operation 
                    edit_df['DEL'] = 'N'
                    
                    #append the edit DF to a single merged dataframe to use at end 
                    merged_df = merged_df.append(edit_df)
        
                    #### DEBUGGING ######
                    # st.write('edit dataframe:')
                    # st.dataframe(edit_df)
                    #######################

                ############ INSERTS ###############
                # handle added row logic and check if there are values in the added rows key
                if key == "added_rows" and len(json_raw['added_rows']) > 0 :
                    add_df_all= pd.DataFrame
                    for key in json_raw['added_rows']:
                        #st.write(key)
                        add_df = pd.DataFrame.from_dict(key, orient='index', columns=['VAL'])
                        add_df= add_df.T

                        #st.write(add_df)
                        #rename columns so we get the column names from the orig DF based on the values  that chaged from those columns
                        for col in add_df.columns:
                            add_df.rename(columns={str(col): df.columns[int(col)-1]}, inplace=True)
        
                        add_df['DEL'] = 'N'
                        add_df_all = pd.concat([add_df], ignore_index=True )
                        
                    #### DEBUGGING ##############
                    # st.write('insert dataframe:')
                    # st.write(add_df_all)    
                    ##### END DEBUGGING          
                    
                    # append the insert DF to a single merged dataframe to use at end             
                    merged_df = merged_df.append(add_df_all)

                ############## DELETES ###################   
                # #handle delete logic and check if there are values in the deleted rows key
                if key == "deleted_rows" and len(json_raw['deleted_rows']) > 0:
                    
                    del_df = pd.DataFrame.from_dict(json_raw['deleted_rows'])
                    del_df.columns = ['VAL']
                    #st.write(df_new)
                    delete_df = pd.merge(del_df, df, left_on='VAL', right_index=True)
            
                    delete_df.drop(columns=['VAL'], inplace=True)
                    delete_df['DEL'] = 'Y'
                    
                    #### DEBUGGING #############
                    # st.write('delete dataframe:')
                    # st.write(delete_df)
                    ##### END DEBUGGING ##################
        
                    # add the delete DF into the merged DF
                    merged_df = merged_df.append(delete_df)
                    
            #now we have all the DFs so we can progess them to JSON and Snowflake
            #merged_df = pd.concat([operation_list], ignore_index=True )
            
            ######## DEBUGGING   ###########
            # st.write('merged dataframe:')
            # st.write(merged_df)
            ####### END DEBUGGING #####$#

            #error handling to make sure some data was changed before trying to process
            if len(json_raw['deleted_rows']) + len(json_raw['edited_cells']) +  len(json_raw['added_rows']) == 0:
                st.error('No changed, deleted or added data was detected. Please make edits before submitting.')
            else: #process the modified data
                
                #print DF to Json
                result = merged_df.to_json(orient="records", date_format='iso')
                parsed = json.loads(result)
                json_data=json.dumps(parsed, indent=4)  
                
                ##### MERGE VIEW ###
                ##create a view to wrap around the JSON data with the same column names as our source table.
                # note: this is a temporary view and is destroyed after the session. if you'd like to view thw 
                #       View DDL you can remove the temporary keyword 
                SRC_VIEW_SQL = "CREATE OR REPLACE VIEW STREAMLIT_MERGE_VW AS (            \
                    SELECT " +   COL_SELECT_FOR_JSON + " FROM                             \
                    ( SELECT PARSE_JSON(' " + json_data + "') as JSON_DATA),              \
                    LATERAL FLATTEN (input => JSON_DATA));"               
                
                session.sql(SRC_VIEW_SQL).collect()

                ########## MERGE STATEMNENT #############
                # we are getting the column lists from the query executed under the COL_LIST
                MERGE_SQL = "MERGE INTO "+table_name + " tgt USING STREAMLIT_MERGE_VW src ON tgt." +PK_COL + " = src." + PK_COL +  " \
                        WHEN MATCHED AND src.DEL = 'Y' THEN DELETE   \
                        WHEN MATCHED THEN UPDATE SET " + COL_LIST_FOR_MERGE_UPDATE + " \
                        WHEN NOT MATCHED THEN INSERT " + COL_LIST_FOR_MERGE_INSERT + ";"
                
                session.sql(MERGE_SQL).collect()
                #drop the view
                session.sql("DROP VIEW STREAMLIT_MERGE_VW").collect() 
                
                st.success ('Edited data successfully written back to Snowflake!') 
                
