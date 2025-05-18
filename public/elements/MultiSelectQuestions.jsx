import { useState, useEffect, useRef } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// Add Popover imports
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
// Add Info icon import and X for multi-select
import { AlertCircle, Upload, FileText, FileIcon, Info, X } from "lucide-react"; // Added X
// Add TooltipProvider import
import { TooltipProvider } from "@/components/ui/tooltip";
// Imports for MultiSelect component
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";

// Helper function to recursively find a question definition by its ID
// within the initial nested structure (mapped by load_questions).
const findQuestionDefinition = (questions, targetId) => {
  for (const q of questions) {
    if (q.questionId === targetId) {
      return q; // Found the question definition
    }
    // Recursively search within the 'subQuestions' property (mapped from JSON's 'sub_questions')
    if (q.subQuestions) {
      for (const key in q.subQuestions) {
        // The items within subQuestions[key] are arrays of question definitions
        const found = findQuestionDefinition(q.subQuestions[key], targetId);
        if (found) {
          return found; // Return the found definition
        }
      }
    }
  }
  return null; // Not found in this branch
};

// Helper function to map question definitions to their state structure
const mapQuestionToState = (qDef, level = 0, parentId = null, parentValue = null) => ({
  ...qDef,
  level,
  parentId,
  parentValue,
  selected: qDef.type === "multi_options" ?
            (Array.isArray(qDef.selected) ? qDef.selected : []) :
            (qDef.selected || ""), // Default for non-multi_options
  isOther: qDef.type === "multi_options" ?
            (Array.isArray(qDef.selected) && qDef.selected.some(s => s === "Other" || s === "Other (Enter your own)")) : // Correctly check elements for "Other" or "Other (Enter your own)"
            (qDef.isOther || false), // Default for non-multi_options
  otherInputValue: qDef.otherInputValue || "", // Initialize for "Other" text in multi_options
});

// MultiSelect component (adapted from provided example)
function FancyMultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Select one or more options...",
}) {
  const inputRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");

  const handleUnselect = (optionToRemove) => {
    onChange(currentSelected.filter((option) => option !== optionToRemove));
  };

  const currentSelected = Array.isArray(selected) ? selected : [];
  const selectables = options.filter((option) => !currentSelected.includes(option));

  return (
    <Command className="overflow-visible bg-transparent">
      <div className="group border border-input px-3 py-0 text-sm ring-offset-background rounded-md focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
        <div className="flex gap-1 flex-wrap items-center">
          {currentSelected.map((option) => (
            <Badge key={option} variant="secondary">
              {option}
              <button
                className="ml-1 ring-offset-background rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                onKeyDown={(e) => { if (e.key === "Enter") { handleUnselect(option); } }}
                onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onClick={() => handleUnselect(option)}
                aria-label={`Remove ${option}`}
              >
                <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
              </button>
            </Badge>
          ))}
          <CommandInput
            ref={inputRef}
            value={inputValue}
            onValueChange={setInputValue}
            onBlur={() => setTimeout(() => setOpen(false), 100)} // Delay to allow click on item
            onFocus={() => setOpen(true)}
            placeholder={currentSelected.length > 0 ? "" : placeholder}
            className="ml-2 bg-transparent outline-none placeholder:text-muted-foreground flex-1 py-0" // Reduced padding here
          />
        </div>
      </div>
      <div className="relative mt-2">
        {open ? ( // Changed condition here: only check for open
          <div className="absolute w-full z-50 top-0 rounded-md border bg-popover text-popover-foreground shadow-md outline-none animate-in">
            <CommandList>
              <CommandEmpty>No results found.</CommandEmpty>
              <CommandGroup style={{ maxHeight: '150px', overflowY: 'auto' }}>
                {selectables.map((option) => (
                  <CommandItem
                    key={option}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    onSelect={() => {
                      setInputValue("");
                      onChange([...currentSelected, option]);
                    }}
                    className={"cursor-pointer"}
                  >
                    {option}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </div>
        ) : null}
      </div>
    </Command>
  );
}

export default function MultiSelectQuestions() {
  // Use the globally injected `props` object.
  const initialQuestions = props.questions || [];
  
  // Track visible questions and their hierarchy
  const [visibleQuestions, setVisibleQuestions] = useState([]);
  
  // Track uploaded files
  const [uploadedFiles, setUploadedFiles] = useState({});
  
  // Track file upload errors
  const [fileErrors, setFileErrors] = useState({});
  
  // Initialize visible questions with the top-level questions
  useEffect(() => {
    setVisibleQuestions(initialQuestions.map(q => mapQuestionToState(q, 0, null, null)));
  }, []); // Assuming initialQuestions is stable from props

  // Get action name from props or use default
  const submitActionName = props.submitActionName || "submit_selections";
  
  // Get hierarchy flag from props or default to false
  const enableHierarchy = props.enableHierarchy || false;

  // Handle file upload
  const handleFileUpload = async (questionId, file) => {
    // Reset error for this question
    setFileErrors(prev => ({ ...prev, [questionId]: null }));
    
    if (!file) return;
    
    // Validate file type (only PDF and DOCX allowed)
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const fileType = file.type;
    
    if (!validTypes.includes(fileType)) {
      setFileErrors(prev => ({ 
        ...prev, 
        [questionId]: "Only PDF and DOCX files are allowed" 
      }));
      return;
    }
    
    // Store file with its base64 content for submission
    try {
      const reader = new FileReader();
      reader.onload = (e) => {
        const base64Content = e.target.result;
        setUploadedFiles(prev => ({ 
          ...prev, 
          [questionId]: {
            name: file.name,
            type: file.type,
            content: base64Content
          }
        }));
        
        // Update the question's selected value to show the filename
        setVisibleQuestions(prev =>
          prev.map(q => {
            if (q.questionId === questionId) {
              return { ...q, selected: file.name };
            }
            return q;
          })
        );
      };
      reader.readAsDataURL(file);
    } catch (error) {
      setFileErrors(prev => ({ 
        ...prev, 
        [questionId]: "Error processing file" 
      }));
    }
  };

  // Handle file removal
  const handleFileRemove = (questionId, e) => {
    // Prevent the click from triggering the file input
    e.stopPropagation();
    
    // Remove the file from uploadedFiles
    setUploadedFiles(prev => {
      const newFiles = { ...prev };
      delete newFiles[questionId];
      return newFiles;
    });
    
    // Clear the selected value in visibleQuestions
    setVisibleQuestions(prev =>
      prev.map(q => {
        if (q.questionId === questionId) {
          return { ...q, selected: "" };
        }
        return q;
      })
    );
    
    // Clear any errors
    setFileErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[questionId];
      return newErrors;
    });
  };

  // Update selections and dynamically adjust visible questions
  const handleSelectChange = (questionId, newValue) => {
    const questionIndex = visibleQuestions.findIndex(q => q.questionId === questionId);
    if (questionIndex === -1) return;

    let updatedQuestions = [...visibleQuestions];
    const answeredQuestionState = updatedQuestions[questionIndex];

    if (answeredQuestionState.type === "multi_options") {
      // Correctly check if "Other" or "Other (Enter your own)" is among the selected values
      const hasOtherSelected = newValue.some(
        option => option === "Other" || option === "Other (Enter your own)"
      );
      updatedQuestions[questionIndex] = {
        ...answeredQuestionState,
        selected: newValue, // newValue is an array from FancyMultiSelect
        isOther: hasOtherSelected,
        // Clear otherInputValue if "Other" is no longer selected, otherwise preserve it
        otherInputValue: hasOtherSelected ? answeredQuestionState.otherInputValue : "",
      };
    } else if (newValue === "Other (Enter your own)" || newValue === "Yes, add additional info") {
      updatedQuestions[questionIndex] = {
        ...answeredQuestionState,
        isOther: true,
        selected: "" 
      };
    } else {
      updatedQuestions[questionIndex] = {
        ...answeredQuestionState,
        isOther: false,
        selected: newValue
      };
    }

    if (enableHierarchy) {
      const targetQuestionDefinition = findQuestionDefinition(initialQuestions, questionId);
      const currentLevel = answeredQuestionState.level || 0;
      
      const questionToRemoveIds = new Set();
      const findChildrenToRemove = (parentId) => {
        const children = updatedQuestions.filter(q => q.parentId === parentId);
        for (const child of children) {
           if (!questionToRemoveIds.has(child.questionId)) {
             questionToRemoveIds.add(child.questionId);
             findChildrenToRemove(child.questionId);
           }
        }
      };
      findChildrenToRemove(questionId);
      let filteredQuestions = updatedQuestions.filter(q => !questionToRemoveIds.has(q.questionId));

      let allNewSubQuestions = [];
      if (targetQuestionDefinition && targetQuestionDefinition.subQuestions) {
        if (answeredQuestionState.type === "multi_options" && Array.isArray(newValue)) {
          newValue.forEach(selectedOptionValue => {
            if (targetQuestionDefinition.subQuestions[selectedOptionValue]) {
              const subQsForThisOption = targetQuestionDefinition.subQuestions[selectedOptionValue].map(sqDef =>
                mapQuestionToState(sqDef, currentLevel + 1, questionId, selectedOptionValue)
              );
              allNewSubQuestions.push(...subQsForThisOption);
            }
          });
        } else if (typeof newValue === 'string' && targetQuestionDefinition.subQuestions[newValue]) {
          allNewSubQuestions = targetQuestionDefinition.subQuestions[newValue].map(sqDef =>
            mapQuestionToState(sqDef, currentLevel + 1, questionId, newValue)
          );
        }
      }

      if (allNewSubQuestions.length > 0) {
        const parentIndexFiltered = filteredQuestions.findIndex(q => q.questionId === questionId);
        if (parentIndexFiltered !== -1) {
            filteredQuestions.splice(parentIndexFiltered + 1, 0, ...allNewSubQuestions);
        } else {
            console.error("Parent question not found in filtered list during sub-question insertion.");
            filteredQuestions = [...filteredQuestions, ...allNewSubQuestions];
        }
      }
      setVisibleQuestions(filteredQuestions);
    } else {
      setVisibleQuestions(updatedQuestions);
    }
  };

  // Update the free-text answer for the question in local state.
  const handleOtherChange = (questionId, value) => {
    setVisibleQuestions(prev =>
      prev.map(q => {
        if (q.questionId === questionId) {
          // If it's a multi_options question and "Other" is active, update otherInputValue
          if (q.type === "multi_options" && q.isOther) {
            return { ...q, otherInputValue: value };
          }
          // Otherwise, update selected (for "text" type or "options" type with "Other")
          return { ...q, selected: value };
        }
        return q;
      })
    );
  };

  // When the user clicks Submit, send an internal message with the appropriate action
  const handleSubmit = () => {
    // Get answers, filtering out any parent/level info we added
    const selections = visibleQuestions.map(q => {
      const { questionId, question, type, options, selected, isOther, otherInputValue } = q;
      
      let finalSelectedValues = selected; // Default to current selected values

      // For multi_options questions, if "Other" was selected and potentially text was entered for it
      if (type === "multi_options" && isOther) {
        let currentSelectionsFromMultiSelect = Array.isArray(selected) ? [...selected] : [];
        
        // Identify the placeholder string for "Other" (e.g., "Other", "Other (Enter your own)")
        // This placeholder would have been selected in the FancyMultiSelect component.
        // We use q.options (destructured as 'options') to find the exact placeholder string.
        const otherOptionPlaceholder = options.find(opt => opt === "Other" || opt === "Other (Enter your own)");

        // Remove the placeholder from the list, as we'll replace it with actual input if available.
        if (otherOptionPlaceholder) {
          currentSelectionsFromMultiSelect = currentSelectionsFromMultiSelect.filter(opt => opt !== otherOptionPlaceholder);
        }

        // If the user typed a non-empty value into the "Other" text input, add that value to the selections list.
        if (otherInputValue && otherInputValue.trim() !== "") {
          currentSelectionsFromMultiSelect.push(otherInputValue.trim());
        }
        // If otherInputValue is empty or only whitespace, the placeholder (if any) remains removed,
        // and no new "other" value is added. This means selecting "Other" and typing nothing
        // results in that "Other" choice not being included in the final list.
        
        finalSelectedValues = currentSelectionsFromMultiSelect;
      }

      const submissionEntry = {
        questionId,
        question,
        type,
        options, // Send the original options definition
        selected: finalSelectedValues, // Send the final, potentially modified, list of selected values
        isOther // Retain the isOther flag, it might provide useful context for the backend
      };

      // The separate `otherText` field previously used for multi_options is no longer needed,
      // as its content is now directly incorporated into the `selected` array.

      return submissionEntry;
    });
    
    // Include file data in the payload
    callAction({
      name: submitActionName,
      payload: { 
        selections,
        files: uploadedFiles
      }
    });
  };

  return (
    // Wrap the component with TooltipProvider
    <TooltipProvider>
      <div className="flex flex-col gap-4">
        {visibleQuestions.map((q, index) => (
          <div 
            key={`${q.questionId}-${index}`} 
            className="flex flex-col gap-2"
            style={{ marginLeft: q.level ? `${q.level * 16}px` : '0' }}
          >
            {/* Wrap question text and icon in a flex container */}
            <div className="mb-2 font-medium flex items-center gap-1.5">
              {q.level > 0 && <span className="text-blue-600">↳ </span>}
              <span>{q.question}</span>
              {/* Add Popover if description exists */}
              {q.description && (
                <Popover>
                  <PopoverTrigger asChild>
                    <Info className="h-4 w-4 text-gray-500 cursor-pointer" />
                  </PopoverTrigger>
                  <PopoverContent className="max-w-xs text-sm">
                    <p>{q.description}</p>
                  </PopoverContent>
                </Popover>
              )}
            </div>
            {q.type === "options" ? (
              <Select
                onValueChange={(value) => handleSelectChange(q.questionId, value)}
                value={!q.isOther ? q.selected : ""}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select an option" />
                </SelectTrigger>
                <SelectContent>
                  {q.options.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : q.type === "multi_options" ? (
              <FancyMultiSelect
                options={q.options || []}
                selected={q.selected} // q.selected is expected to be an array by FancyMultiSelect
                onChange={(selectedOptions) => handleSelectChange(q.questionId, selectedOptions)}
                placeholder="Select options..."
              />
            ) : null}
            {(q.isOther || q.type === "text") && (
              <textarea
                value={
                  (q.type === "multi_options" && q.isOther)
                    ? q.otherInputValue
                    : q.selected
                }
                placeholder="Enter your answer"
                onChange={e => {
                  handleOtherChange(q.questionId, e.target.value);
                  if (e.target) {
                    e.target.style.height = 'auto';
                    e.target.style.height = `${e.target.scrollHeight}px`;
                  }
                }}
                rows={1}
                className="w-full rounded-lg border border-gray-200 bg-white shadow-sm px-3 py-2 text-sm focus:outline-none focus:ring-2 transition-all min-h-[40px] resize-none placeholder-gray-400"
                style={{
                  overflow: 'hidden',
                  '--tw-ring-color': 'hsl(var(--ring))',
                  '--tw-border-color': 'hsl(var(--primary))'
                }}
              />
            )}
            {q.type === "attachment" && (
              <div className="space-y-2">
                <Label htmlFor={`file-${q.questionId}`} className="cursor-pointer w-full">
                  <div className={`flex flex-col items-center justify-center p-1 border-2 border-dashed rounded-lg transition-colors relative
                    ${q.selected ? 'bg-blue-50 border-blue-300' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'}`}>
                    {q.selected ? (
                      <>
                        {/* Remove file button */}
                        <button 
                          type="button"
                          onClick={(e) => handleFileRemove(q.questionId, e)}
                          className="absolute top-2 right-2 p-1 bg-red-100 hover:bg-red-200 rounded-full text-red-500 hover:text-red-700 transition-colors"
                          aria-label="Remove file"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                        </button>
                        <FileText className="h-8 w-8 text-blue-500 mb-2" />
                        <div className="text-blue-600 font-medium">{q.selected}</div>
                        <div className="text-xs text-gray-500 mt-1">Click to change file</div>
                      </>
                    ) : (
                      <>
                        <Upload className="h-8 w-8 text-gray-400 mb-2" />
                        <div className="font-medium">Upload Document</div>
                        <div className="text-xs text-gray-500 mt-1">PDF or DOCX files only</div>
                      </>
                    )}
                  </div>
                </Label>
                <Input
                  id={`file-${q.questionId}`}
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={(e) => handleFileUpload(q.questionId, e.target.files[0])}
                />
                {fileErrors[q.questionId] && (
                  <div className="flex items-center p-2 mt-2 bg-red-50 border border-red-200 text-red-700 rounded-md">
                    <AlertCircle className="h-4 w-4 mr-2" />
                    <div className="text-sm">{fileErrors[q.questionId]}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        <Button onClick={handleSubmit}>Submit Answers</Button>
      </div>
    </TooltipProvider>
  );
}