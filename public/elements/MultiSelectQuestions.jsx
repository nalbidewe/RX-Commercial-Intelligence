import { useState, useEffect } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, Upload, FileText, FileIcon } from "lucide-react";

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
      questionId: q.questionId || q.abbrev,
      question: q.question,
      type: q.type || "options",
      options: q.options || q.value || [],
      selected: "",
      isOther: false,
      subQuestions: q.subQuestions || q.sub_questions || {},
      level: 0,
      parentId: null,
      parentValue: null,
      mandatory: q.mandatory || false
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

  // Find a question in the question structure (including sub-questions) by ID
  const findQuestionById = (questions, id) => {
    // First check directly in the array
    const directMatch = questions.find(q => q.questionId === id || q.abbrev === id);
    if (directMatch) return directMatch;
    
    // Then check in sub-questions/subQuestions
    for (const q of questions) {
      const subQsMap = q.subQuestions || q.sub_questions || {};
      
      for (const [answerValue, subQs] of Object.entries(subQsMap)) {
        if (!Array.isArray(subQs)) continue;
        
        // Look for the question in this sub-questions array
        const subMatch = subQs.find(sq => sq.questionId === id || sq.abbrev === id);
        if (subMatch) return subMatch;
        
        // Recursively check each sub-question's subQuestions
        for (const subQ of subQs) {
          const subSubQsMap = subQ.subQuestions || subQ.sub_questions || {};
          
          for (const [subAnsValue, subSubQs] of Object.entries(subSubQsMap)) {
            if (!Array.isArray(subSubQs)) continue;
            
            const subSubMatch = subSubQs.find(ssq => ssq.questionId === id || ssq.abbrev === id);
            if (subSubMatch) return subSubMatch;
          }
        }
      }
    }
    
    return null;
  };

  // Update selections and dynamically adjust visible questions
  const handleSelectChange = (questionId, value) => {
    // Find the question that was answered
    const questionIndex = visibleQuestions.findIndex(q => q.questionId === questionId);
    if (questionIndex === -1) return;

    // Create a copy of the current questions
    const updatedQuestions = [...visibleQuestions];
    
    // Handle special cases: "Other" or "Yes, add additional info"
    if (value === "Other (Enter your own)" || value === "Yes, add additional info") {
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        isOther: true,
        selected: ""
      };
    } else {
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        isOther: false,
        selected: value
      };
    }
    
    // Handle hierarchical questions if enabled
    if (enableHierarchy) {
      // Get the current question and its level
      const currentQuestion = updatedQuestions[questionIndex];
      const level = currentQuestion.level || 0;
      
      // Find all children of this question to remove them
      const questionToRemoveIds = new Set();
      const findChildrenToRemove = (parentId, startIdx = 0) => {
        for (let i = startIdx; i < updatedQuestions.length; i++) {
          const q = updatedQuestions[i];
          if (q.parentId === parentId) {
            questionToRemoveIds.add(q.questionId);
            // Recursively find children of this question too
            findChildrenToRemove(q.questionId, i + 1);
          }
        }
      };
      
      findChildrenToRemove(questionId, questionIndex + 1);
      
      // Filter out questions that need to be removed
      const filteredQuestions = updatedQuestions.filter(q => !questionToRemoveIds.has(q.questionId));
      
      // Check if this question has sub-questions for the selected value
      const subQsMap = currentQuestion.subQuestions || {};
      if (subQsMap[value] && Array.isArray(subQsMap[value])) {
        // Transform the sub-questions into the format needed for visible questions
        const subQuestions = subQsMap[value].map(sq => ({
          questionId: sq.questionId || sq.abbrev,
          question: sq.question,
          type: sq.type || "options",
          options: sq.options || sq.value || [],
          selected: "",
          isOther: false,
          subQuestions: sq.subQuestions || sq.sub_questions || {},
          level: level + 1,
          parentId: questionId,
          parentValue: value,
          mandatory: sq.mandatory || false
        }));
        
        // Insert the sub-questions immediately after their parent
        filteredQuestions.splice(questionIndex + 1, 0, ...subQuestions);
      }
      
      setVisibleQuestions(filteredQuestions);
    } else {
      // For non-hierarchical forms, just update the question
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
    const selections = visibleQuestions.map(({ questionId, question, type, options, selected, isOther, mandatory }) => ({
      questionId, 
      question, 
      type, 
      options, 
      selected, 
      isOther,
      mandatory
    }));
    
    // Check if all mandatory questions are answered
    const unansweredMandatory = selections.filter(q => 
      q.mandatory && (!q.selected || q.selected.trim() === "")
    );
    
    if (unansweredMandatory.length > 0) {
      // Alert the user about unanswered mandatory questions
      alert(`Please answer all required questions before submitting.`);
      return;
    }
    
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
    <div className="flex flex-col gap-4">
      {visibleQuestions.map((q, index) => (
        <div 
          key={`${q.questionId}-${index}`} 
          className="flex flex-col gap-2"
          style={{ marginLeft: q.level ? `${q.level * 16}px` : '0' }}
        >
          <div className="mb-2 font-medium">
            {q.level > 0 && <span className="text-blue-600">↳ </span>}
            {q.question} {q.mandatory && <span className="text-red-500">*</span>}
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
            <Input
              value={q.selected}
              placeholder="Enter your answer"
              onChange={(e) => handleOtherChange(q.questionId, e.target.value)}
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
  );
}