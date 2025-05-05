import { useState, useEffect } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// Add Popover imports
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
// Add Info icon import
import { AlertCircle, Upload, FileText, FileIcon, Info } from "lucide-react";
// Add TooltipProvider import
import { TooltipProvider } from "@/components/ui/tooltip";

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
    setVisibleQuestions(initialQuestions.map(q => ({
      ...q,
      level: 0,
      parentId: null,
      parentValue: null
    })));
  }, []);

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
  const handleSelectChange = (questionId, value) => {
    // First, find the question that was answered in the visible list
    const questionIndex = visibleQuestions.findIndex(q => q.questionId === questionId);
    if (questionIndex === -1) return;

    // Create a copy of the current questions
    let updatedQuestions = [...visibleQuestions];
    const answeredQuestionState = updatedQuestions[questionIndex];

    // Update the state of the answered question (selected value, isOther)
    if (value === "Other (Enter your own)" || value === "Yes, add additional info") {
      updatedQuestions[questionIndex] = {
        ...answeredQuestionState,
        isOther: true,
        selected: "" // Clear selection for 'Other' initially
      };
    } else {
      updatedQuestions[questionIndex] = {
        ...answeredQuestionState,
        isOther: false,
        selected: value
      };
    }

    // Handle hierarchical questions if enabled
    if (enableHierarchy) {
      // Find the definition of the question that was just answered using the helper
      // Search within the initialQuestions structure (which uses 'subQuestions')
      const targetQuestionDefinition = findQuestionDefinition(initialQuestions, questionId);

      // Remove any existing sub-questions that depended on the previous answer
      const level = answeredQuestionState.level || 0;
      const questionToRemoveIds = new Set();

      // Find all child questions to remove (and their children recursively)
      const findChildrenToRemove = (parentId) => {
        // Iterate through a *copy* of updatedQuestions or use indices carefully
        // to avoid issues with modifying the array while iterating.
        const children = updatedQuestions.filter(q => q.parentId === parentId);
        for (const child of children) {
           if (!questionToRemoveIds.has(child.questionId)) { // Avoid redundant checks/infinite loops
             questionToRemoveIds.add(child.questionId);
             findChildrenToRemove(child.questionId); // Recursive call
           }
        }
      };

      // Start removal process from the current question's ID
      findChildrenToRemove(questionId);

      // Filter out questions marked for removal
      let filteredQuestions = updatedQuestions.filter(q => !questionToRemoveIds.has(q.questionId));

      // Add new sub-questions if the definition and the selected value have them
      if (targetQuestionDefinition && targetQuestionDefinition.subQuestions && targetQuestionDefinition.subQuestions[value]) {
        const subQuestionsToAdd = targetQuestionDefinition.subQuestions[value].map(sq => ({
          // Map the definition (sq) to the state structure
          questionId: sq.questionId, // Use questionId from the processed definition
          question: sq.question,
          type: sq.type,
          options: sq.options,
          selected: "", // Initial state
          isOther: false, // Initial state
          // *** CORRECTION: Use sq.subQuestions as processed by load_questions ***
          subQuestions: sq.subQuestions || {}, // Pass definitions for the *next* level
          // Hierarchy tracking
          level: level + 1,
          parentId: questionId,
          parentValue: value
        }));

        // Find the index of the parent question *in the filtered list*
        const parentIndexFiltered = filteredQuestions.findIndex(q => q.questionId === questionId);
        if (parentIndexFiltered !== -1) {
            // Insert sub-questions right after their parent question
            filteredQuestions.splice(parentIndexFiltered + 1, 0, ...subQuestionsToAdd);
        } else {
            // Fallback: append if parent somehow disappeared (should not happen)
            console.error("Parent question not found in filtered list during sub-question insertion.");
            filteredQuestions = [...filteredQuestions, ...subQuestionsToAdd];
        }
      }

      setVisibleQuestions(filteredQuestions);
    } else {
      // For non-hierarchical forms, just update the single question's state
      setVisibleQuestions(updatedQuestions);
    }
  };

  // Update the free-text answer for the question in local state.
  const handleOtherChange = (questionId, value) => {
    setVisibleQuestions(prev =>
      prev.map(q => {
        if (q.questionId === questionId) {
          return { ...q, selected: value };
        }
        return q;
      })
    );
  };

  // When the user clicks Submit, send an internal message with the appropriate action
  const handleSubmit = () => {
    // Get answers, filtering out any parent/level info we added
    const selections = visibleQuestions.map(({ questionId, question, type, options, selected, isOther }) => ({
      questionId, 
      question, 
      type, 
      options, 
      selected, 
      isOther
    }));
    
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
            ) : null}
            {(q.isOther || q.type === "text") && (
              <textarea
                value={q.selected}
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
                  <div className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg transition-colors relative
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